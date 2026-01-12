import numpy as np
import json
from steam_web_api import Steam
from scipy.sparse import load_npz, csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

X_tfidf = load_npz("data/game_vectors.npz")

N_GAMES = 81650

def get_game_vector(appid, appid_to_index):
    idx = appid_to_index.get(str(appid))
    if idx is None:
        return None
    return X_tfidf[idx]

def get_names(appids, name_index_json):
    with open(name_index_json, "r") as f:
        name_index = json.load(f)
        output_names = [name_index.get(appid, f"Game name not in database: {appid}") for appid in appids]
        return output_names 


class UserEmbedding:

    def __init__(self, profile_url, steam_key):
        self.steam = Steam(steam_key)
        self.steamid = self.get_user_steamid(profile_url)
        self.username = self.get_username()
        self.user_games = self.get_user_games()
        self.recent_games = self.get_user_recent_games()
        self.user_vector = None

    def resolve_vanity_url(self, parsed_vanity_url):
        username = parsed_vanity_url[-1]
        try:
            user = self.steam.users.search_user(username)
            return user["player"]["steamid"]
        except Exception as e:
            raise Exception(f"Error fetching user steamid: {e}")

    def get_user_steamid(self, profile_url):
        if "/" not in profile_url:
            raise Exception(f"Invalid profile url")
        parsed_url = profile_url.split("/")
        if parsed_url[-1] == "":
            del parsed_url[-1]
        if "id" in parsed_url:
            return self.resolve_vanity_url(parsed_url)
        elif "profiles" in parsed_url:
            try:
                steamid = parsed_url[-1]
                int(steamid)
                return steamid
            except Exception as e:
                raise Exception("Invalid profile url")
        else:
            raise Exception("Invalid profile url")
    
    def get_username(self):
        try:
            user = self.steam.users.get_user_details(self.steamid)
            return user["player"]["personaname"]
        except Exception as e:
            print(f"Error fetching username: {e}")
            return ""
    
    def get_user_games(self):
        try:
            user_games = self.steam.users.get_owned_games(self.steamid)
            if user_games.get("total_count") == 0:
                print("No games found on the user profile. Stopping.")
                exit(0)
            return user_games["games"]
        except Exception as e:
            print(f"Error fetching user games: {e}")
            return []

    def get_user_recent_games(self):
        try:
            recent_games = self.steam.users.get_user_recently_played_games(self.steamid)
            if recent_games.get("total_count") == 0:
                print("No recent games found")
                return []
            return recent_games["games"]
        except Exception as e:
            print(f"Error fetching user recent games: {e}")
            return []
        
    def build_user_vector(self):
        recent_games = {game.get("appid"):
                            {"forever": game.get("playtime_forever"),
                             "2weeks": game.get("playtime_2weeks")}
                        for game in self.recent_games}
        
        all_games = {game.get("appid"):
                        {"forever": game.get("playtime_forever"),
                         "2weeks": 0} if game.get("appid") not in recent_games
                         else recent_games[game.get("appid")]
                    for game in self.user_games}
        
        user_vec = None
        total_weight = 0.0

        for appid, playtimes in all_games.items():
            with open("data/appid_to_index.json", "r") as f:
                appid_to_index = json.load(f)
                game_vec = get_game_vector(appid, appid_to_index)
            
            if game_vec is None:
                continue
            
            playtime_2weeks = playtimes.get("2weeks", 0)
            playtime_forever =  playtimes.get("forever", 0)
            
            w = np.log1p(playtime_forever) 

            if playtime_2weeks > 0:
                w *= 1 + playtime_2weeks / playtime_forever
            
            if user_vec is None:
                user_vec = w * game_vec
            else:
                user_vec += w * game_vec

            total_weight += w

        if user_vec is None:
            self.user_vector = None
            return
        if total_weight == 0:
            self.user_vector = None
            return

        user_vec /= np.linalg.norm(user_vec.data)
        self.user_vector = user_vec

    def _compute_similarity(self):
        return cosine_similarity(self.user_vector, X_tfidf).flatten()
    
    def recommend_games(self, n_games):
        if self.user_vector is None:
            print("Insuficient playtime or game data")
            return None
        scores = self._compute_similarity()
        with open("data/index_to_appid.json") as f:
            index_to_appid = json.load(f)

        n_owned_games = len(self.user_games)
        owned_appids = [game.get("appid") for game in self.user_games]

        best_idxs = np.argpartition(scores, -(n_games + n_owned_games))[-(n_games + n_owned_games):]
        best_scores = scores[best_idxs]
        best_idxs = best_idxs[np.argsort(-best_scores)]
        best_scores = scores[best_idxs]

        recommendations_appid = []
        for i in best_idxs:
            if len(recommendations_appid) >= n_games:
                break
            appid = index_to_appid[str(i)]
            if int(appid) in owned_appids:
                continue
            recommendations_appid.append(index_to_appid[str(i)])
        
        recommendations_names = get_names(recommendations_appid, "data/name_index.json")
        return list(zip(recommendations_names, best_scores))
    
    def random_not_played_games(self, n_games, power=0.75):
        if self.user_vector is None:
            owned_appids = []
        else:
            owned_appids = [game.get("appid") for game in self.user_games]
        
        # weights = np.exp(-power*np.arange(N_GAMES))
        weights = 1/np.power(np.arange(N_GAMES) + 1, power)
        weights = weights/np.sum(weights)
        random_inds = sorted(np.random.choice(np.arange(N_GAMES), p=weights, size=n_games))
        random_inds = np.sort(random_inds)
        
        random_games = []
        with open("data/steam_games_detailed.ndjson", "r", encoding="utf-8") as f:
            c = 0
            for i, line in enumerate(f):
                if i >= random_inds[c]:
                    game = list(json.loads(line).items())[0]
                    gameid = game[0]
                    if gameid in owned_appids:
                        continue
                    game_name = game[1].get("name")
                    random_games.append((gameid, game_name))
                    c += 1
                    if c >= n_games:
                        break
        
        np.random.shuffle(random_games)
        return random_games

        
        

if __name__ == "__main__":
    KEY = "110B8B0590263C8C00B6120E6EE1326D"

    user = UserEmbedding("https://steamcommunity.com/profiles/76561198135163136", KEY)
    user.build_user_vector()
    print("Personalized games: ", user.recommend_games(10))
    print("Random popular (kind of) games: ", user.random_not_played_games(10))