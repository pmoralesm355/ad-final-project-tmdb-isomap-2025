from __future__ import annotations
from typing import Any, Dict, List, Optional
import os, datetime as dt
import requests, requests_cache, backoff
from dotenv import load_dotenv
load_dotenv()

class TMDBAPIUtils:
    def __init__(self, api_key: Optional[str]=None, access_token: Optional[str]=None,
                 language: str="en-US", cache_name: str="tmdb_cache",
                 expire_after: int=86400)->None:
        self.api_key = api_key or os.getenv("TMDB_API_KEY")
        self.access_token = access_token or os.getenv("TMDB_ACCESS_TOKEN")
        self.language = language
        self.session = requests_cache.CachedSession(cache_name, expire_after=expire_after)
        self.base_url = "https://api.themoviedb.org/3"

    def _headers(self)->Dict[str,str]:
        h = {"Accept":"application/json"}
        if self.access_token: h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def _params(self, extra: Optional[Dict[str,Any]]=None)->Dict[str,Any]:
        p: Dict[str,Any] = {"language": self.language}
        if self.api_key and not self.access_token: p["api_key"] = self.api_key
        if extra: p.update(extra)
        return p

    @backoff.on_exception(backoff.expo, (requests.RequestException,), max_tries=3)
    def _get(self, path: str, params: Optional[Dict[str,Any]]=None)->Dict[str,Any]:
        r = self.session.get(f"{self.base_url}{path}", headers=self._headers(), params=self._params(params))
        r.raise_for_status()
        return r.json()

    def search_person(self, name: str, page: int=1)->List[Dict[str,Any]]:
        return self._get("/search/person", {"query": name, "page": page}).get("results", [])

    def get_movie_cast(self, movie_id: str, limit: int=5, exclude_ids: Optional[List[int]]=None)->List[Dict[str,Any]]:
        exclude = set(exclude_ids or [])
        cast = self._get(f"/movie/{movie_id}/credits").get("cast", []) or []
        cast_sorted = sorted(cast, key=lambda c: (c.get("order", 9999), c.get("cast_id", 9999999)))
        out: List[Dict[str,Any]] = []
        for m in cast_sorted:
            if m.get("id") in exclude: continue
            if limit is not None and m.get("order", 9999) >= limit: continue
            out.append({"id": m.get("id"), "name": m.get("name"),
                        "character": m.get("character"), "order": m.get("order"),
                        "movie_id": movie_id})
        return out

    def get_movie_credits_for_person(self, person_id: str, start_date: Optional[str]=None,
                                     end_date: Optional[str]=None)->List[Dict[str,Any]]:
        cast = self._get(f"/person/{person_id}/movie_credits").get("cast", []) or []
        def pd(s: Optional[str]):
            try: return dt.datetime.strptime(s, "%Y-%m-%d").date() if s else None
            except: return None
        sd, ed = pd(start_date), pd(end_date)
        res: List[Dict[str,Any]] = []
        for it in cast:
            rd = pd(it.get("release_date"))
            if sd and (rd is None or rd < sd): continue
            if ed and (rd is None or rd > ed): continue
            res.append({"person_id": int(person_id), "title": it.get("title") or it.get("original_title"),
                        "release_date": it.get("release_date"), "movie_id": it.get("id"),
                        "character": it.get("character")})
        res.sort(key=lambda x: (x.get("release_date") or ""), reverse=True)
        return res