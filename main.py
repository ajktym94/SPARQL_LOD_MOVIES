import json
import requests
import numpy as np
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef, BNode, Literal, Namespace, Graph
from rdflib.namespace import FOAF, DCTERMS, XSD, RDF, SDO, OWL

######################################################################################################################

# Load RDF file
g = Graph()
g.parse("movie.owl")

######################################################################################################################
'''
Function to retrieve DBPedia link from title
Input: Title
Output: DBpedia link
'''
def get_dbpedia_link(title):
    query = '''
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX movie: <https://www.imdb.com/>

            SELECT ?remote
            WHERE {
                ?movie movie:title "'''+title+'''" .
                ?movie owl:sameAs ?remote .
            }
            '''
    result = g.query(query)
    for i in result:
        db_link = str(i[0])
        break
    return db_link

######################################################################################################################

'''
Function to retrieve Director's name from movie title
Input: Title
Output: Director's name
'''

def get_director(title):
    db_link = get_dbpedia_link(title)
    query = '''
            SELECT ?remote_value
            WHERE {
                    <'''+db_link+'''> dbp:director ?remote_value
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    try:
        return results['results']['bindings'][0]['remote_value']['value']
    except:
        print("Sorry, no results")


######################################################################################################################
'''
Function to retrieve a Director's list of budgets from his/her URI
Input: Director's URI
Output: Director's budget list
'''
def get_budget(director):
    try:
        query = '''
                SELECT ?budget
                WHERE {
                        ?movie dbo:director <'''+director+'''> .
                        ?movie dbo:budget ?budget
                    }
                '''   
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        return [record['budget']['value'] for record in results['results']['bindings']]
    except:
        print("Sorry! no results")


######################################################################################################################
'''
Function to calculate average budget from a list of budgets
Input: Director's URI
Output: Director's average budget
'''

def get_avg_budget(director):
    result = get_budget(director)
    result_int = list()
    try:
        for i in result:
            if 'E' in i:
                b,e = i.split('E')
                num = float(b)*np.power(10,int(e))
                result_int.append(num)
            else:
                result_int.append(float(i))
        print("The average budget of "+director.split('/')[-1]+"'s movies is: Dollars", np.average(result_int))
        return np.average(result_int)
    except:
        print("Sorry! No results")


######################################################################################################################
'''
Function to retrieve a movie's actors
Input: Movie's URI
Output: Movie's actors
'''

def get_coactors(link):
    query = '''
            SELECT ?remote_value
            WHERE {
                    <'''+link+'''> dbo:starring ?remote_value .
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    try:
        if len(results['results']['bindings']) > 1:
            return results['results']['bindings']
    except:
        print("Sorry, no results")

######################################################################################################################
'''
Function to retrieve the movies in which the 2 top actors acted together
Input: Actors list
Output: Movies in which the top 2 actors acted together
'''

def get_coactors_movies(actors):
    query = '''
            SELECT ?film
            WHERE {
                    ?film dbo:starring <'''+actors[0]['remote_value']['value']+'''> .
                    ?film dbo:starring <'''+actors[1]['remote_value']['value']+'''> .
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    try:
#         if len(results['results']['bindings']) > 1:
        return results['results']['bindings']
    except:
        print("Sorry, no results")

######################################################################################################################
'''
Function to retrieve a movie's related links
Input: Movie's URI
Output: Related links
'''

def get_related_movies(db_link):
    query = '''
            SELECT ?remote_value
            WHERE {
                    <'''+db_link+'''> dbo:wikiPageWikiLink ?remote_value
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    try:
        return results['results']['bindings']
    except:
        print("Sorry, no results")

######################################################################################################################
'''
Function to check if a related item is a movie or not
Input: Results from get_related_movies()
Output: List of movies
'''

def check_movie(results):
    for result in results:
        query = '''
        SELECT ?remote_value
        WHERE {
                <'''+result['remote_value']['value']+'''> rdf:type ?remote_value
            }
        '''
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        output = sparql.query().convert()
        for rv in output['results']['bindings']:
            if rv['remote_value']['value'] == 'http://dbpedia.org/ontology/Film':
                        query = '''
                                SELECT ?remote_value
                                WHERE {
                                        <'''+result['remote_value']['value']+'''> dbp:name ?remote_value
                                    }
                                '''
                        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
                        sparql.setQuery(query)
                        sparql.setReturnFormat(JSON)
                        movie_name = sparql.query().convert()
                        try:
                            print(movie_name['results']['bindings'][0]['remote_value']['value'])        
                        except:
                            continue

######################################################################################################################
'''
Function to retrieve the main crew members of a movie
Input: Movie's URI
Output: List of main crew members
'''

def get_crew(link):
    query = '''
            SELECT ?dir ?dop ?comp ?music ?screen ?prod group_concat(?star; separator=",")
            WHERE {
                    <'''+link+'''> dbo:director ?dir .
                    <'''+link+'''> dbo:cinematography ?dop .
                    <'''+link+'''> dbo:musicComposer ?comp .
                    <'''+link+'''> dbp:music ?music .
                    <'''+link+'''> dbo:producer ?prod .
                    <'''+link+'''> dbo:starring ?star .
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    crew = sparql.query().convert()
    return crew

######################################################################################################################
'''
Function to find the youngest crew member
Input: List of the URIs of the crew
Output: Youngest crew member and his/her DOB
'''

def get_youngest(links):
    query = '''
        SELECT ?bd ?name WHERE
        {
        {SELECT ?bd ?name
        WHERE {
                <'''+links[0]+'''> dbo:birthDate ?bd .
                <'''+links[0]+'''> dbp:name ?name .
            }}'''
    if len(links) > 1:
        for link in links:
            query = query + '''UNION
                {SELECT ?bd ?name
            WHERE {
                    <'''+link+'''> dbo:birthDate ?bd .
                    <'''+link+'''> dbp:name ?name .
                }}
            '''
    query = query + '''}
        ORDER BY DESC(?bd)
    '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    movie_name = sparql.query().convert()
    print("The youngest main crew member is", movie_name['results']['bindings'][0]['name']['value'],"born on", movie_name['results']['bindings'][0]['bd']['value']) 

######################################################################################################################
'''
Function to retrieve an actor's longest movie
Input: Actor's URI
Output: Longest movie
'''

def get_longest_movie(link):
    actor = get_coactors(link)[0]['remote_value']['value']
    actor_name = get_actor_name(actor)
#     try:
    query = '''
            SELECT ?runtime ?name
            WHERE {
                    ?movie dbo:starring <'''+actor+'''> .
                    ?movie dbo:runtime ?runtime .
                    ?movie dbp:name ?name .
                }
            ORDER BY DESC(?runtime)
            '''   
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    print("The longest movie of", actor_name, "is", results['results']['bindings'][0]['name']['value'], "running", float(results['results']['bindings'][0]['runtime']['value'])/3600,"hours")
#     except:
#         print("Sorry! no results")

######################################################################################################################
'''
Function to retrieve the movie name from it's URI
Input: Movie URI
Output: Movie name
'''

def get_movie_name(link):
    query = '''
            SELECT ?remote_value
            WHERE {
                    <'''+link+'''> dbp:name ?remote_value
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    movie_name = sparql.query().convert()
    print(movie_name['results']['bindings'][0]['remote_value']['value']) 

######################################################################################################################
'''
Function to retrieve an actor's name from his/her URI
Input: Actor URI
Output: Actor name
'''

def get_actor_name(link):
    query = '''
            SELECT ?remote_value
            WHERE {
                    <'''+link+'''> dbp:name ?remote_value
                }
            '''
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    actor_name = sparql.query().convert()
    return actor_name['results']['bindings'][0]['remote_value']['value']

######################################################################################################################

if __name__=="__main__":
    menu = '''
    MENU
    1. Get related movies
    2. Get average budget of all movies of a particular movie's director
    3. Get other movies where the coactors of a particular movie acted together 
    4. Get youngest main crew member of a movie
    5. Get the longest movie of a movie's top actor
    '''
    print(menu)

    choice = input("Enter your choice: ")
    if choice == "1":
        title = input("\nEnter the movie name:")
        link = get_dbpedia_link(title)
        movies = get_related_movies(link)
        print("\nOther movies related to",title, "are: \n")
        check_movie(movies)
    elif choice == "2":
        title = input("\nEnter the movie name:")
        director = get_director(title)
        get_avg_budget(director)
    elif choice == "3":
        title = input("\nEnter the movie name:")
        link = get_dbpedia_link(title)
        actors = get_coactors(link)
        print("\nThe top 2 actors are:")
        try:
            for actor in actors[:2]:
                print(get_actor_name(actor['remote_value']['value']))
            movies = get_coactors_movies(actors)
            print("\nThe movies where they acted together are:")
            for movie in movies:
                get_movie_name(movie['film']['value'])
        except:
            print("Sorry! No results.")
    elif choice == "4":
        title = input("\nEnter the movie name:")
        link = get_dbpedia_link(title)
        result = get_crew(link)
        l = [r['value'].split(',') for r in result['results']['bindings'][0].values()]
        links = [y for x in l for y in x]
        get_youngest(links)
    elif choice == "5":
        title = input("\nEnter the movie name:")
        link = get_dbpedia_link(title)
        get_longest_movie(link)
    else:
        print("Sorry! Invalid Choice")

######################################################################################################################