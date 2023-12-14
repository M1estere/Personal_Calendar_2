import uuid
from datetime import *

from PyQt5.QtCore import Qt
from cassandra.cluster import Cluster


cluster = Cluster(['192.168.1.18'], port=9042)
session = cluster.connect('db0')


def add_user(nickname, name, password):
    user = get_user_info(nickname)
    if user is not None:
        return -1

    try:
        user_id = uuid.uuid4()
        session.execute(f"INSERT INTO users(id, nickname, name, password) " +
                        f"VALUES ({user_id}, '{nickname}', '{name}', '{password}')")
    except Exception as e:
        print('Add user error')
        print(e)
        return -2

    return id


def add_note(user_id, note_title, note_desc, note_creation_date, note_colour) -> bool:
    try:
        update_date = datetime.now()
        metadata_id = create_metadata(note_creation_date, update_date)

        note_id = uuid.uuid4()
        session.execute(f"INSERT INTO notes (id, creation_date, metadata_id, title, user_id, description) " +
                        f"VALUES ({note_id}, '{note_creation_date}', {metadata_id}, '{note_title}', {user_id}, '{note_desc}')")

        stage_id = uuid.uuid4()
        session.execute(f"INSERT INTO stage (id, note_colour, note_id, user_id) " +
                        f"VALUES ({stage_id}, '{note_colour}', {note_id}, {user_id})")
        return True if add_note_to_days(stage_id, note_creation_date) else False
    except Exception as e:
        print('Add note notes/stage error')
        print(e)
        return False


def create_metadata(creation_date, update_date):
    try:
        metadata_id = uuid.uuid4()
        session.execute(f"INSERT INTO metadata (id, creation_date, update_date) " +
                        f"VALUES ({metadata_id}, '{creation_date}', '{update_date}')")

        return metadata_id
    except Exception as e:
        print('Create metadata error')
        print(e)
        return -1


def add_note_to_days(stage_id, creation_date):
    date_record = record_for_date(creation_date)
    if date_record is not None:
        return insert_note_for_date(date_record, stage_id)

    try:
        stages_set = set()
        stages_set.add(str(stage_id))
        session.execute(f"INSERT INTO days (id, date, stages_id) " +
                        f"VALUES ({uuid.uuid4()}, '{creation_date}', {stages_set})")
    except Exception as e:
        print('Add note to days error')
        print(e)
        return -2

    return 1


def insert_note_for_date(date_record, stage_id):
    try:
        stage_id = str(stage_id)
        session.execute(f"UPDATE days SET stages_id = stages_id + {{'{stage_id}'}} " +
                        f"WHERE id = {date_record.id}")
    except Exception as e:
        print('Update error')
        print(e)
        return False

    return True


def record_for_date(date_to_check):
    try:
        request = session.execute(f"SELECT * FROM days " +
                                  f"WHERE date = '{date_to_check}'").one()
    except Exception as e:
        print('Get date error')
        print(e)
        return None

    return request


def save_edited_note(note_id, note_title, note_desc, note_colour):
    note = get_note(note_id)

    if note is None:
        return -1

    try:
        update_time = datetime.now()
        metadata = session.execute(f"SELECT * " +
                                   f"FROM metadata " +
                                   f"WHERE id = {note.metadata_id}").one()
        session.execute(f"UPDATE metadata " +
                        f"SET update_date = '{update_time}' " +
                        f"WHERE id = {metadata.id}")
        session.execute(f"UPDATE notes " +
                        f"SET title = '{note_title}', description = '{note_desc}'" +
                        f"WHERE id = {note_id}")

        edit_note_in_date(note_id, note_colour)
    except Exception as e:
        print('Save edited note error')
        print(e)
        return -2

    return 1


def edit_note_in_date(note_id, note_colour):
    try:
        stages = session.execute(f"SELECT * FROM stage").all()
        for stage in stages:
            if stage.note_id == note_id:
                session.execute(f"UPDATE stage " +
                                f"SET note_colour = '{note_colour}' " +
                                f"WHERE id = {stage.id}")
    except Exception as e:
        print('Edit note in date error')
        print(e)
        return -1


def get_note(note_id):
    try:
        request = session.execute(f"SELECT * " +
                                  f"FROM notes " +
                                  f"WHERE id = {note_id}")
        return request.one()
    except Exception as e:
        print('Get note error')
        print(e)
        return None


def get_note_last_edit(note_id):
    try:
        note = session.execute(f"SELECT * " +
                               f"FROM notes " +
                               f"WHERE id = {note_id}").one()
        metadata = session.execute(f"SELECT * " +
                                   f"FROM metadata " +
                                   f"WHERE id = {note.metadata_id}").one()

        return metadata.update_date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print('Get note last update error')
        print(e)
        return ''


def delete_note(date, note_id):
    note_doc = get_note(note_id)

    if note_doc is None:
        return -1

    try:
        delete_note_from_day(date, note_id)

        metadata_id = note_doc.metadata_id

        session.execute(f"DELETE FROM metadata " +
                        f"WHERE id = {metadata_id}")
        session.execute(f"DELETE FROM notes " +
                        f"WHERE id = {note_id}")
    except Exception as e:
        print('Delete note metadata/notes error')
        print(e)
        return -2

    return 1


def delete_note_from_day(date, note_id):
    try:
        stage_to_delete = session.execute(f"SELECT * FROM stage " +
                                          f"WHERE note_id = {note_id}").one()
        day_to_change = session.execute(f"SELECT * " +
                                        f"FROM days " +
                                        f"WHERE date = '{date}'").one()

        stage_id = stage_to_delete.id

        session.execute(f"DELETE FROM stage " +
                        f"WHERE id = {stage_to_delete.id}")

        session.execute(f"UPDATE days " +
                        f"SET stages_id = stages_id - {{'{stage_id}'}} " +
                        f"WHERE id = {day_to_change.id}")
    except Exception as e:
        print('Delete from day error')
        print(e)
        return -2

    return 1


def get_user_notes(user_id, note_creation_date):
    try:
        request = session.execute(f"SELECT * " +
                                  f"FROM notes " +
                                  f"WHERE user_id = {user_id}")
        notes_collection = request.all()

        if notes_collection is None:
            return None
        else:
            return get_date_notes(notes_collection, note_creation_date)
    except Exception as e:
        print('Get user notes error')
        print(e)
        return None


def get_date_notes(col, chosen_date):
    result_collection = list()
    for element in col:
        creation_date = element.creation_date.date()

        if str(creation_date) == str(chosen_date):
            result_collection.append(element)

    return result_collection


def get_notes_for_day(date, dates_dict):
    res_dict = dict()
    for date_pr, notes_list in dates_dict.items():
        if date.toString(Qt.ISODate) == date_pr:
            res_dict[date_pr] = notes_list

    return res_dict


def get_user_days_notes(user_id):
    days = session.execute(f"SELECT * " +
                           f"FROM days").all()

    res_dict = dict()
    for day in days:
        new_key = day.date.strftime('%Y-%m-%d')
        res_dict[new_key] = list()
        try:
            notes_for_day = session.execute(f"SELECT * " +
                                            f"FROM notes " +
                                            f"WHERE creation_date = '{day.date}'").all()
            for note in notes_for_day:
                if note.user_id == user_id:
                    res_dict[new_key].append(note)
        except Exception as e:
            print('Get user days error')
            print(e)
            return -1

    return res_dict


def get_note_colour(note_id):
    try:
        request = session.execute(f"SELECT * " +
                                  f"FROM stage " +
                                  f"WHERE note_id = {note_id}").one()

        return request.note_colour
    except Exception as e:
        print('Get note colour error')
        print(e)
        return -1


def get_user_info(nickname):
    try:
        request = session.execute(f"SELECT id, nickname, name, password " +
                                  f"FROM users " +
                                  f"WHERE nickname = '{nickname}'")
        return request.one()
    except Exception as e:
        print('Get user info error')
        print(e)
        return -1


def get_user_by_id(user_id):
    try:
        user = session.execute(f"SELECT * FROM users " +
                               f"WHERE id = {user_id}").one()
        return user
    except Exception as e:
        print('Get user by id error')
        print(e)
        return -1


def update_user(user_id, new_nickname, new_name, new_password):
    user = get_user_by_id(user_id)
    if user is None:
        return -1

    try:
        session.execute(f"UPDATE users " +
                        f"SET nickname = '{new_nickname}', name = '{new_name}', password = '{new_password}' " +
                        f"WHERE id = {user_id}")
    except Exception as e:
        return -2

    return 1


def try_log_user(nickname, password):
    user_info = get_user_info(nickname)
    if user_info is None:
        return -1

    if user_info.password != password:
        return -2

    return user_info.id
