from os import getenv
from time import time
import exceptions
from pymongo import MongoClient, errors

MONGO_PASSWORD = getenv("MONGO_PASSWORD")

cluster = MongoClient(
    f"mongodb+srv://Makeathon:{MONGO_PASSWORD}@cluster0.ufg1w.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
print(cluster.test)
db = cluster["Team_Verification"]
teams = db["Teams"]


def add_team(team_name: str, leader: int, members: list, channel_form=False, channels_list=None):
    if channels_list is None:
        channels_list = []
    if channel_form is False:
        try:
            teams.insert_one(
                {"_id": team_name.lower(), "leader": leader, "members": members, "channels": channels_list})
        except errors.DuplicateKeyError:
            raise exceptions.DuplicateInDatabaseError
    else:
        teams.update_one({"_id": team_name.lower()}, {"$set": {"channels": channels_list}})


def member_delta(leader: int, member_id: int, delta: int = 1):
    if delta == 1:
        teams.update_one({"leader": leader}, {"$push": {"members": member_id}})
    else:
        teams.update_one({"leader": leader}, {"$pull": {"members": member_id}})


def lookup(team_name: str):
    team_name = team_name.lower()
    try:
        team_data = dict(teams.find_one({"_id": team_name}))
    except TypeError:
        raise exceptions.NotInDataBaseError
    if team_data is not None:
        return {"leader": team_data["leader"], "members": team_data["members"]}
    else:
        raise exceptions.NotInDataBaseError


def channel_lookup(leader: int):
    team_info = dict(teams.find_one({"leader": leader}))
    return team_info['channels']


def cleancode(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content


def calculate_ping():
    start_time = time()
    pong = db.command('ping')
    finish_time = time()
    ping_time = f"{round((finish_time - start_time) * 1000, 2)}  ms"

    start_time = time()
    teams.update_one({'_id': "Test Team [NEEDED FOR DEBUGGING]"}, {"$inc": {'leader': 1}})
    finish_time = time()
    write_time = f"{round((finish_time - start_time) * 1000, 2)}  ms"

    start_time = time()
    teams.find_one({'_id': "Test Team [NEEDED FOR DEBUGGING]"})
    finish_time = time()
    read_time = f"{round((finish_time - start_time) * 1000, 2)}  ms"

    if pong['ok'] == 1:
        return [ping_time, write_time, read_time]
    else:
        return "Server didn't ping back"
