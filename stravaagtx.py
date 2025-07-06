from strava2gpx import strava2gpx
from stravalib import Client
from datetime import datetime
import requests
import gpxpy
import gpxpy.parser
import base64
import csv
import os
import asyncio
import gpxpy.geo


async def main():
    '''
    put in your Strava Api client_id, refresh_token, and client_secret
    '''
    client_id = os.getenv('STRAVA_CLIENT_ID')
    print (client_id)
    refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')

    country_translation = {
        "España": "Espanya",
        "Тоҷикистон": "Tadjikistan",
        "中国": "Xina",
        "France": "França",
        "Italia": "Itàlia",
        "Argentina": "Argentina",
        "Bolivia": "Bolívia",
        "Colombia": "Colòmbia",
        "Slovenija": "Eslovènia",
        "Hrvatska": "Croàcia",
        "Bosna i Hercegovina / Босна и Херцеговина": "Bòsnia i Hercegovina",
        "Crna Gora / Црна Гора": "Montenegro",
        "Shqipëria": "Albània",
        "Ελλάς": "Grècia",
        "Türkiye": "Turquia",
        "საქართველო": "Geòrgia",
        "Հայաստան": "Armènia",
        "ایران": "Iran",
        "پاکستان": "Pakistan",
        "India": "Índia",
        "नेपाल": "Nepal",
        "বাংলাদেশ": "Bangladesh",
        "ประเทศไทย": "Tailàndia",
        "Malaysia": "Malàisia",
        "Singapore": "Singapur",
        "Australia": "Austràlia",
        "New Zealand / Aotearoa": "Nova Zelanda",
        "Chile": "Xile",
        "Perú": "Perú",
        "Ecuador": "Equador",
        "España": "Espanya"
    }

    def get_country_from_coordinates(lat, lon):
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
        headers = {"User-Agent": "VueltaAlMundoBot/1.0"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            address = data.get("address", {})
    
            country = address.get("country", "Desconocido")
            state = address.get("state", "")
            
            if state == "Catalunya":
                return "Catalunya"
            else:
                return country_translation.get(country, country)  # Devuelve el país en catalán si está en el diccionario
    
        else:
            return "Error"

    def get_starting_coordinates(gpx_file_path):
        with open(gpx_file_path, "r") as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            if gpx.tracks and gpx.tracks[0].segments and gpx.tracks[0].segments[0].points:
                first_point = gpx.tracks[0].segments[0].points[0]
                return first_point.latitude, first_point.longitude
        return None, None
    
    def calculate_distance(gpx_file):
        with open(gpx_file, 'r') as file:
            gpx = gpxpy.parse(file)
            distance = gpx.length_3d() / 1000  # Convertir a kilómetros
            return distance

    def calculate_days_since_start(date_str):
        start_date = datetime(2025, 11, 23)
        current_date = datetime.strptime(date_str, "%Y-%m-%d")
        return (current_date - start_date).days + 1
    
    def actualizar_nombre(actividad_id, nuevo_nombre, token_acceso):
        """Actualiza el nombre de la actividad en Strava"""
        url = f'https://www.strava.com/api/v3/activities/{actividad_id}'
        headers = {'Authorization': f'Bearer {token_acceso}'}
        data = {'name': nuevo_nombre}
        respuesta = requests.put(url, headers=headers, data=data)
        respuesta.raise_for_status()
        return respuesta.json()
    
    def update_csv(file_name, distance, date_str, strava_url, pais):
        csv_file = 'routes.csv'
        stage = 1
    
        # Si el archivo ya existe, leer el número de la última etapa
        if os.path.exists(csv_file):
            with open(csv_file, mode='r', newline='') as file:
                reader = csv.reader(file)
                # Leer todas las filas para encontrar el número de la última etapa
                rows = list(reader)
                if rows:
                    stage = int(rows[-1][0]) + 1
                else: 
                    stage = 1
    
        # Calcular el número de días
        day = calculate_days_since_start(date_str)
    
        # Escribir la nueva fila en el archivo CSV
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([stage, day, date_str, distance, file_name, strava_url, pais])

   
    # create an instance of strava2gpx
    s2g = strava2gpx(client_id, client_secret, refresh_token)

    # connect to the Strava API
    await s2g.connect()
    
    activities_list = await s2g.get_activities_list()
    lastactivity = activities_list[0]
    activity_id = lastactivity[1]
    
    client = Client()
    client.access_token = os.getenv('STRAVA_ACCESS_TOKEN')
    client.refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
    client.token_expires = int(float(os.getenv('EXPIRES_AT')))
    
    athlete = client.get_athlete()
    print(f"Connectat com a {athlete.firstname} {athlete.lastname}")
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    filename = lastactivity[2]
    filename = filename.replace(":","")

    # write activity to output.gpx by activity id
    # if os.listdir()[0] == str(filename)+".gpx":
    #    print ("Mateixa activitat")
    # else:
    #    print ("Diferent activitat")
    with open("latest_file.txt", "r") as file:
        latest_file_name = file.read().strip()
        
    if latest_file_name == str(filename)+".gpx":
        print ("Mateixa activitat")
    else:
        print ("Diferent activitat")
        await s2g.write_to_gpx(activity_id, filename)       
        with open("latest_file.txt", "w") as file:
            file.write(str(filename)+".gpx")
        with open("total_distance.txt", "r") as file:
            total_distance = float(file.read().strip())
        new_distance = calculate_distance(str(filename)+".gpx")
        total_distance += new_distance
        with open("total_distance.txt", "w") as file:
            file.write(str(total_distance))
        print(f"Total distance accumulated: {total_distance} km")

        date_of_route = filename[:10]
        strava_activity_url = f"https://www.strava.com/activities/{activity_id}"

        lat, lon = get_starting_coordinates(str(filename)+".gpx")
        if lat is not None and lon is not None:
            country = get_country_from_coordinates(lat, lon)
        else:
            country = "Error"
        
        update_csv(str(filename)+".gpx", new_distance, date_of_route, strava_activity_url, country)

        numero_dia = calculate_days_since_start(date_of_route)
        nuevo_nombre = f"Dia {numero_dia} de la XXX"
        token_acceso = client.access_token
        actualizar_nombre(activity_id, nuevo_nombre, token_acceso)
        
if __name__ == '__main__':
    asyncio.run(main()) 
