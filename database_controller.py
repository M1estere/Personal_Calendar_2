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
        id = uuid.uuid4()
        session.execute(f"INSERT INTO users(id, nickname, name, password) " +
                                  f"VALUES ({id}, '{nickname}', '{name}', '{password}')")
    except Exception as e:
        return -2

    return id


def add_note(user_id, note_title, note_desc, note_creation_date, note_colour) -> bool:
    try:
        update_date = datetime.now()
        metadata_id = create_metadata(note_creation_date, update_date)
        note_id = uuid.uuid4()
        session.execute(f"INSERT INTO notes (id, creation_date, metadata_id, note_colour, title, user_id, description) " +
                                  f"VALUES ({note_id}, '{note_creation_date}', {metadata_id}, '{note_colour}', '{note_title}', {user_id}, '{note_desc}')")
        return True #if add_note_to_days(user_id, note_id, note_creation_date, note_colour) else False
    except Exception as e:
        return False


def create_metadata(creation_date, update_date):
    metadata_id = uuid.uuid4()
    session.execute(f"INSERT INTO metadata (id, creation_date, update_date) " +
                              f"VALUES ({metadata_id}, '{creation_date}', '{update_date}')")

    return metadata_id


def add_note_to_days(user_id, note_id, creation_date, note_colour):
    days_collection = database['days_data']

    date_record = record_for_date(creation_date)
    if date_record is not None:
        return insert_note_for_date(user_id, note_id, note_colour, date_record)

    data_list = [
        {
            'note_1': {
                'user_id': ObjectId(user_id),
                'note_id': ObjectId(note_id),
                'note_colour': note_colour
            },
        }
    ]

    data_dict = {
        'date': creation_date,
        'notes_data': data_list
    }

    try:
        days_collection.insert_one(data_dict)
    except Exception as e:
        return -2

    return 1


def insert_note_for_date(user_id, note_id, note_colour, date_record):
    days_collection = database['days_data']

    notes_list = date_record['notes_data']
    num_for_new_record = len(notes_list) + 1

    new_note_dict = {
        f'note_{num_for_new_record}': {
            'user_id': ObjectId(user_id),
            'note_id': ObjectId(note_id),
            'note_colour': note_colour
        }
    }

    notes_list.append(new_note_dict)
    res_dict = {
        'notes_data': notes_list
    }

    try:
        days_collection.update_one({'date': date_record['date']}, {"$set": res_dict})
    except Exception as e:
        return False

    return True


def record_for_date(date_to_check):
    days_collection = database['days_data']
    return days_collection.find_one({'date': date_to_check})


def save_edited_note(user_id, note_id, note_title, note_desc, note_creation_date, note_colour):
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
                        f"SET title = '{note_title}', description = '{note_desc}', note_colour = '{note_colour}'" +
                        f"WHERE id = {note_id}")

        # edit_note_in_date(note_id, note_creation_date, note_colour)
    except Exception as e:
        return -2

    return 1


def edit_note_in_date(note_id, date, note_colour):
    days_collection = database['days_data']

    notes_list = list()
    for day in days_collection.find({}):
        if day['date'] != date:
            continue

        day_notes = day['notes_data']
        for note in day_notes:
            if list(note.items())[0][1]['note_id'] == note_id:
                list(note.items())[0][1]['note_colour'] = note_colour

            notes_list.append(note)

    res_dict = {
        'notes_data': notes_list
    }

    try:
        days_collection.update_one({'date': date}, {"$set": res_dict})
    except Exception as e:
        return -2

    return 1


def get_note(note_id):
    request = session.execute(f"SELECT * " +
                              f"FROM notes " +
                              f"WHERE id = {note_id}")
    return request.one()


def delete_note(date, note_id):
    note_doc = get_note(note_id)

    if note_doc is None:
        return -1

    try:
        metadata_id = note_doc.metadata_id

        session.execute(f"DELETE FROM metadata " +
                        f"WHERE id = {metadata_id}")
        session.execute(f"DELETE FROM notes " +
                        f"WHERE id = {note_id}")
        # delete_note_from_day(date, note_id)
    except Exception as e:
        return -2

    return 1


def delete_note_from_day(date, note_id):
    days_collection = database['days_data']

    notes_list = list()
    for day in days_collection.find({}):
        if day['date'] != date:
            continue

        day_notes = day['notes_data']
        for note in day_notes:
            if list(note.items())[0][1]['note_id'] == note_id:
                continue
            else:
                notes_list.append(note)

    res_dict = {
        'notes_data': notes_list
    }

    try:
        if len(notes_list) < 1:
            days_collection.delete_one({'date': date})
        else:
            days_collection.update_one({'date': date}, {"$set": res_dict})
    except Exception as e:
        return -2

    return 1


def get_user_notes(user_id, note_creation_date):
    request = session.execute(f"SELECT * " +
                              f"FROM notes " +
                              f"WHERE user_id = {user_id}")
    notes_collection = request.all()

    if notes_collection is None:
        return None
    else:
        return get_date_notes(notes_collection, note_creation_date)


def get_date_notes(col, chosen_date):
    result_collection = list()
    for element in col:
        creation_date = element.creation_date.date()

        if str(creation_date) == str(chosen_date):
            result_collection.append(element)

    return result_collection


def get_list_for_calendar(user_id):
    all_user_notes_for_date = get_all_notes_data(user_id)
    return all_user_notes_for_date


def get_notes_for_day(date, collection):
    res_list = list()
    for element in collection:
        if date.toString(Qt.ISODate) == element['date']:
            res_list.append(element)

    return res_list


def get_notes_for_id(user_id, collection):
    t_collection = list()
    for element_dict in collection:
        notes_data = element_dict['notes_data']

        notes_list = list()
        for note in notes_data:
            if list(note.items())[0][1]['user_id'] == ObjectId(user_id):
                notes_list.append(note)

        element_dict['notes_data'] = notes_list
        t_collection.append(element_dict)

    return t_collection


def get_all_notes_data(user_id):
    request = session.execute(f"SELECT * " +
                              f"FROM days")
    days_collection = request.all()

    res_list = list()

    for day in days_collection:
        for stage_id in day.stage_ids.split(' '):
            request = session.execute(f"SELECT * " +
                                      f"FROM stage " +
                                      f"WHERE id = '{stage_id}'")
            stage = request.one()


def get_user_info(nickname):
    request = session.execute(f"SELECT id, nickname, name, password " +
                              f"FROM users " +
                              f"WHERE nickname = '{nickname}'")
    return request.one()


def get_user_by_id(user_id):
    return session.execute(f"SELECT * FROM users " +
                           f"WHERE id = {user_id}").one()


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
