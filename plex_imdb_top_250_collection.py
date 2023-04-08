# ------------------------------------------------------------------------------
#
#       Automated IMDB Top 250 Plex collection script inspired by /u/SwiftPanda16
#       Set Secure Connections to Preferred or this will not work
#                         *** Use at your own risk! ***
#   *** I am not responsible for damages to your Plex server or libraries. ***
#
# ------------------------------------------------------------------------------

import csv
import json
import os
import shutil
import sys
import time

import requests
from lxml import html
from plexapi.server import PlexServer

### Plex server details ###
# Make sure that under Network settings you have Secure connections set to Preferred or Disabled
PLEX_URL = 'http://localhost:32400'
PLEX_TOKEN = 'xxxxxxxxxx'

### Existing movie library details ###
MOVIE_LIBRARY_NAME = 'Movies'

### New IMDB Top 250 library details ###
IMDB_CHART_URL = 'http://www.imdb.com/chart/top'

# lists to use
# https://letterboxd.com/dave/list/official-top-250-narrative-feature-films/
# https://letterboxd.com/chris_coke/list/letterboxds-top-250-science-fiction-films/
# https://letterboxd.com/darrencb/list/letterboxds-top-250-horror-films/
LETTERBOXD_CHART_URL = 'https://letterboxd.com/dave/list/official-top-250-narrative-feature-films/'
LETTERBOXD_URL = 'https://letterboxd.com'
IMDB_COLLECTION_NAME = 'IMDB Top 250'
LETTERBOXD_COLLECTION_NAME = 'Letterboxd Official Top 250 Narrative Feature Films'

### The Movie Database details ###
# Enter your TMDb API key if your movie library is using "The Movie Database" agent.
# This will be used to convert the TMDb IDs to IMDB IDs.
# You can leave this blank '' if your movie library is using the "Plex Movie" agent.
TMDB_API_KEY = ''


##### CODE BELOW #####

TMDB_REQUEST_COUNT = 0  # DO NOT CHANGE


def add_collection(library_key, rating_key, collection_name):
    headers = {"X-Plex-Token": PLEX_TOKEN}
    params = {"type": 1,
              "id": rating_key,
              "collection[0].tag.tag": collection_name,
              "collection.locked": 1
              }

    url = "{base_url}/library/sections/{library}/all".format(
        base_url=PLEX_URL, library=library_key)
    r = requests.put(url, headers=headers, params=params)


def remove_collection(library_key, rating_key, collection_name):
    headers = {"X-Plex-Token": PLEX_TOKEN}
    params = {"type": 1,
              "id": rating_key,
              "collection[].tag.tag-": collection_name
              }

    url = "{base_url}/library/sections/{library}/all".format(
        base_url=PLEX_URL, library=library_key)
    r = requests.put(url, headers=headers, params=params)


def get_imdb_id_from_tmdb(tmdb_id):
    global TMDB_REQUEST_COUNT

    if not TMDB_API_KEY:
        return None

    # Wait 10 seconds for the TMDb rate limit
    if TMDB_REQUEST_COUNT >= 40:
        time.sleep(10)
        TMDB_REQUEST_COUNT = 0

    params = {"api_key": TMDB_API_KEY}

    url = "https://api.themoviedb.org/3/movie/{tmdb_id}".format(
        tmdb_id=tmdb_id)
    r = requests.get(url, params=params)

    TMDB_REQUEST_COUNT += 1

    if r.status_code == 200:
        movie = json.loads(r.text)
        return movie['imdb_id']
    else:
        return None


def get_imdb_id_from_letterboxd(url):
    ### Retrieve IMDB data from Letterboxd movie page ###
    r = requests.get(url)
    tree = html.fromstring(r.content)

    movie_title = tree.xpath(
        "//div[contains(@class, 'react-component film-poster')]/@data-film-name")[0]
    movie_year = tree.xpath(
        "//div[contains(@class, 'react-component film-poster')]/@data-film-release-year")[0]

    try:
        imdb_url = tree.xpath(
            "//p[@class='text-link text-footer']//a[@data-track-action='IMDb']/@href")
        imdb_id = imdb_url[0].rsplit('/', 2)[-2]
    except:
        # tmdb_url = tree.xpath("//p[@class='text-link text-footer']//a[@data-track-action='TMDb']/@href")
        # tmdb_id = tmdb_url[0].rsplit('/', 2)[-2]

        # Gangs of Wasseypur is one combined film on IMDB but is two separate on Letterboxd
        if movie_title == "Gangs of Wasseypur - Part 2":
            imdb_id = "tt1954470"
        else:
            imdb_id = 0

    return movie_title, movie_year, imdb_id


def letterboxd_top_250(library_language):
    ### Get the Letterboxd Top 250 List ###
    print("Retrieving the Letterboxd Official Top 250 Narrative Feature Films list...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    top_250_titles, top_250_years, top_250_ids = [], [], []

    if os.path.isfile('letterboxd_top_250.csv'):
        refresh = input(
            "Stored Letterboxd Top 250 exists. Do you want to force a refresh? (y/n): ")
        if refresh == 'n':
            csv_read_data = {}
            with open('letterboxd_top_250.csv', 'r') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                for i, row in enumerate(csv_reader):
                    csv_read_data[i] = row
            top_250_ids = csv_read_data[0]
            top_250_titles = csv_read_data[1]
            top_250_years = csv_read_data[2]

    if not os.path.isfile('letterboxd_top_250.csv') or refresh == 'y':
        print(
            "Please be patient. This will take longer than creating the IMDB Top 250 list.")
        print()
        page_number = 1
        indicator = True
        while indicator:
            r = requests.get(LETTERBOXD_CHART_URL + 'page/{}'.format(page_number),
                             headers={'Accept-Language': library_language})
            tree = html.fromstring(r.content)

            # http://stackoverflow.com/questions/35101944/empty-list-is-returned-from-imdb-using-python-lxml
            # https://www.w3schools.com/html/default.asp
            # https://www.w3schools.com/xml/xpath_syntax.asp
            # https://stackoverflow.com/questions/4531995/getting-attribute-using-xpath
            top_250_letterboxd_url = tree.xpath(
                "//ul[contains(@class, 'poster-list -p125 -grid film-list')]//div[@class='poster-container numbered-list-item']/@data-target-link")
            if top_250_letterboxd_url:
                for url in top_250_letterboxd_url:
                    title, year, imdb_id = get_imdb_id_from_letterboxd(
                        LETTERBOXD_URL + url)
                    top_250_titles.append(title)
                    top_250_years.append(year)
                    top_250_ids.append(imdb_id)
                page_number += 1
            else:
                indicator = False
        with open('letterboxd_top_250.csv', 'w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            csv_writer.writerow(top_250_ids)
            csv_writer.writerow(top_250_titles)
            csv_writer.writerow(top_250_years)

    return top_250_ids, top_250_titles, top_250_years


def imdb_top_250(library_language):
    ### Get the IMDB Top 250 List ###
    print("Retrieving the IMDB Top 250 list...")
    r = requests.get(IMDB_CHART_URL, headers={
                     'Accept-Language': library_language})
    tree = html.fromstring(r.content)

    # http://stackoverflow.com/questions/35101944/empty-list-is-returned-from-imdb-using-python-lxml
    top_250_titles = tree.xpath(
        "//table[contains(@class, 'chart')]//td[@class='titleColumn']/a/text()")
    top_250_years = tree.xpath(
        "//table[contains(@class, 'chart')]//td[@class='titleColumn']/span/text()")
    top_250_ids = tree.xpath(
        "//table[contains(@class, 'chart')]//td[@class='ratingColumn']/div//@data-titleid")
    return top_250_ids, top_250_titles, top_250_years


def plex_movie_list():
    ### Create PlexServer object and list of movies ###
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    except Exception as e:
        print("No Plex server found at: {base_url}".format(base_url=PLEX_URL))
        print("Exiting script.")
        sys.exit()

    print("Retrieving a list of movies from the '{library}' library in Plex...".format(
        library=MOVIE_LIBRARY_NAME))
    try:
        movie_library = plex.library.section(MOVIE_LIBRARY_NAME)
        movie_library_key = movie_library.key
        library_language = movie_library.language
        all_movies = movie_library.all()
        return movie_library, movie_library_key, library_language, all_movies
    except:
        print("The '{library}' library does not exist in Plex.".format(
            library=MOVIE_LIBRARY_NAME))
        print("Exiting script.")
        sys.exit()


def imdb_id_mapping(all_movies):
    """
    Create a dictionary consisting of {imdb_id: movie} pairs for the Plex library. 
    """
    plex_library_imdb_ids = []
    imdb_map = {}
    for m in all_movies:
        for guid in m.guids:
            if 'imdb://' in guid.id:
                imdb_id = guid.id.split('imdb://')[1]
                break
            elif 'tmdb://' in guid.id:
                tmdb_id = guid.id.split('tmdb://')[1]
                imdb_id = get_imdb_id_from_tmdb(tmdb_id)
                break
            else:
                imdb_id = None

        if imdb_id is not None:
            plex_library_imdb_ids.append(imdb_id)
            imdb_map[imdb_id] = m
    return plex_library_imdb_ids, imdb_map


def set_collection(top_250_ids, imdb_map, movie_library_key, collection_name):
    ### Create the plex collection ###
    print("Setting the collection for the '{}' library...".format(MOVIE_LIBRARY_NAME))
    in_library_idx = []
    for i, imdb_id in enumerate(top_250_ids):
        movie = imdb_map.pop(imdb_id, None)
        if movie:
            add_collection(movie_library_key, movie.ratingKey, collection_name)
            in_library_idx.append(i)
    for movie in imdb_map.values():
        remove_collection(movie_library_key, movie.ratingKey, collection_name)
    return in_library_idx


def get_found_missing_list(top_250_ids, top_250_titles, top_250_years, in_library_idx):
    # Get list of missing IMDB Top 250 movies
    missing_top_250 = [(idx, imdb) for idx, imdb in enumerate(zip(top_250_ids, top_250_titles, top_250_years))
                       if idx not in in_library_idx]

    # Get list of found IMDB Top 250 movies
    found_top_250 = [(idx, imdb) for idx, imdb in enumerate(zip(top_250_ids, top_250_titles, top_250_years))
                     if idx in in_library_idx]
    return missing_top_250, found_top_250


def print_results(missing_top_250, found_top_250):
    columns, _ = shutil.get_terminal_size(fallback=(80, 24))
    print("="*columns)
    print(
        f"\nNumber of Top {len(missing_top_250)+len(found_top_250)} movies in the library: {len(found_top_250)}")
    print(f"Number of missing Top {len(missing_top_250)+len(found_top_250)} movies: {len(missing_top_250)}")
    print(
        f"\nList of found Top {len(missing_top_250)+len(found_top_250)} movies:\n")

    for idx, (imdb_id, title, year) in found_top_250:
        print("{idx}\t{imdb_id}\t{title} {year}".format(
            idx=idx+1, imdb_id=imdb_id, title=title, year=year))

    print(
        f"\nList of missing Top {len(missing_top_250)+len(found_top_250)} movies:\n")

    for idx, (imdb_id, title, year) in missing_top_250:
        print("{idx}\t{imdb_id}\t{title} {year}".format(
            idx=idx+1, imdb_id=imdb_id, title=title, year=year))


def run_imdb_top_250():
    movie_library, movie_library_key, library_language, all_movies = plex_movie_list()
    top_250_ids, top_250_titles, top_250_years = imdb_top_250(library_language)
    plex_library_imdb_ids, imdb_map = imdb_id_mapping(all_movies)
    in_library_idx = set_collection(
        top_250_ids, imdb_map, movie_library_key, IMDB_COLLECTION_NAME)
    missing_top_250, found_top_250 = get_found_missing_list(
        top_250_ids, top_250_titles, top_250_years, in_library_idx)
    print_results(missing_top_250, found_top_250)


def run_letterboxd_top_250():
    movie_library, movie_library_key, library_language, all_movies = plex_movie_list()
    top_250_ids, top_250_titles, top_250_years = letterboxd_top_250(
        library_language)
    plex_library_imdb_ids, imdb_map = imdb_id_mapping(all_movies)
    in_library_idx = set_collection(
        top_250_ids, imdb_map, movie_library_key, LETTERBOXD_COLLECTION_NAME)
    missing_top_250, found_top_250 = get_found_missing_list(
        top_250_ids, top_250_titles, top_250_years, in_library_idx)
    print_results(missing_top_250, found_top_250)


def run_crossover_top_250():
    movie_library, movie_library_key, library_language, all_movies = plex_movie_list()
    top_250_ids, top_250_titles, top_250_years = imdb_top_250(library_language)
    top_250_ids_two, top_250_titles_two, top_250_years_two = letterboxd_top_250(
        library_language)
    top_250_ids_crossover = sorted(
        list(set(top_250_ids) & set(top_250_ids_two)))
    top_250_titles_crossover = [
        top_250_titles[top_250_ids.index(x)] for x in top_250_ids_crossover]
    top_250_years_crossover = [
        top_250_years[top_250_ids.index(x)] for x in top_250_ids_crossover]
    plex_library_imdb_ids, imdb_map = imdb_id_mapping(all_movies)
    in_library_idx = set_collection(
        top_250_ids_crossover, imdb_map, movie_library_key, "IMDB & Letterboxd Top 250 Crossover")
    missing_top_250, found_top_250 = get_found_missing_list(
        top_250_ids_crossover, top_250_titles_crossover, top_250_years_crossover, in_library_idx)
    print_results(missing_top_250, found_top_250)


if __name__ == "__main__":
    columns, rows = shutil.get_terminal_size(fallback=(80, 24))
    print("="*columns)
    print("Automated Plex collection script".center(columns))
    print("="*columns)

    menu = {}
    menu['1'] = ".  IMDB Top 250"
    menu['2'] = ".  Letterboxd Top 250"
    menu['3'] = ".  IMDB Top 250 & Letterboxd Top 250"
    menu['4'] = ".  Quit"

    options = menu.keys()
    for entry in options:
        print("{}{}".format(entry, menu[entry]))

    selection = input("Please select an option:  ")
    if selection == '1':
        print()
        run_imdb_top_250()
    elif selection == '2':
        print()
        run_letterboxd_top_250()
    elif selection == '3':
        print()
        run_crossover_top_250()
    else:
        print()
        print("Unknown Option Selected!")

    print("="*columns)
    print("Done".center(columns))
    print("="*columns)

    input("Press Enter to finish...")
