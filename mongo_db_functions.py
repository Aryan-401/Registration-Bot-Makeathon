from os import getenv
from time import time
import os

from pymongo import MongoClient, errors

import exceptions

MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")

cluster = MongoClient(
    f"mongodb+srv://Makeathon:{MONGO_PASSWORD}@cluster0.ufg1w.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
print(cluster.test)
db = cluster["Team_Verification"]
teams = db["Teams"]


def add_team(team_name: str, member_id: int, role_id: int):
    try:
        teams.insert_one({"_id": team_name.lower(), "member_id": [member_id], "role_id": role_id})
        return 1
    except errors.DuplicateKeyError:
        if len(teams.find_one({"_id": team_name.lower()})["member_id"]) >= 5:
            raise exceptions.BrokenRequest(message="This Team is already full. Please Join another team. If you "
                                                   "believe this is an error, Contact a Moderator")
        teams.update_one({"_id": team_name.lower()}, {"$push": {"member_id": member_id}})
        return 0


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
