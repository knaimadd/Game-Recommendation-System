import json
import steamspypi

FIELDS = {
    "appid",
    "name",
    "developer",
    "publisher",
    "positive",
    "negative",
    "owners",
    "average_forever",
    "average_2weeks",
    "price",
}

def extract_games_steamspi(num_pages: int):
    games = dict()
    data_request = dict()
    data_request['request'] = 'all'
    for page in range(num_pages):
        data_request['page'] = str(page)
        try:
            games_on_page = steamspypi.download(data_request)
            games.update(games_on_page)
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
    return games

def append_games_to_json(data: dict, filename: str):
    with open(filename, "a", encoding="utf-8") as f:
        for appid, game in data.items():
            filtered = {k: game.get(k) for k in FIELDS}

            record = {
                str(appid): filtered
            }

            json.dump(record, f, ensure_ascii=False)
            f.write("\n")

def load_games_ndjson(filename: str) -> dict:
    games = {}

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            games.update(record) 

    return games

def extract_game_details_steamspi(appid: str):
    data_request = {
        'request': 'appdetails',
        'appid': appid
    }
    try:
        game_details = steamspypi.download(data_request)
        return {k: game_details.get(k) for k in ["genre", "tags"]}
    except Exception as e:
        print(f"Error fetching details for appid {appid}: {e}")
        return None
    
def iter_games_ndjson(filename):
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            yield next(iter(json.loads(line).items()))
    

def add_fields_ndjson(input_file: str, output_file: str, tags_lookup: dict, genre_lookup: dict):
    with open(input_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8") as fout:

        for line in fin:
            record = json.loads(line)  # record = {"814630": {...fields...}}

            # extract appid and inner data
            appid, data = next(iter(record.items()))
            
            # enrich the inner data
            data["tags"] = tags_lookup.get(appid, [])  # convert key to int if needed
            data["genre"] = genre_lookup.get(appid, [])

            # write back with the same appid as key
            json.dump({appid: data}, fout, ensure_ascii=False)
            fout.write("\n")