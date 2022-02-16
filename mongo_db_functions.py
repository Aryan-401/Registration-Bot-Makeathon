import exceptions
from pymongo import MongoClient, errors

# MONGO_PASSWORD = getenv("MONGO_PASSWORD")

cluster = MongoClient(f"mongodb+srv://Bot_User:{'MONGODB_TOKEN'}@cluster0.ufg1w.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
d = cluster.test
print(d)
db= cluster["Team_Verification"]
teams= db["Teams"]


def add_team(team_name: str, leader: int, members: list, channel_form = False, channels_list: list = []):
    if channel_form is False:
        try:
            teams.insert_one({"_id": team_name.lower(), "leader": leader, "members": members, "channels": channels_list})
        except errors.DuplicateKeyError:
            raise exceptions.DuplicateInDatabaseError
    else:
        teams.update_one({"_id": team_name.lower()}, {"$set": {"channels": channels_list}})
    

def member_delta(leader: int ,member_id: int, delta: int = 1):
    if delta == 1:
        teams.update_one({"leader": leader}, {"$push": {"members": member_id}})
    else:
        teams.update_one({"leader": leader}, {"$pull": {"members": member_id}})



def lookup(team_name: str):
    team_name = team_name.lower()
    try:
        team_data = dict(teams.find_one({"_id": team_name}))
    except NoneType:
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