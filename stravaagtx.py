from strava2gpx import strava2gpx
from stravalib import Client
from datetime import datetime
import requests
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

    def calculate_distance(gpx_file):
        with open(gpx_file, 'r') as file:
            gpx = gpxpy.parse(file)
            distance = gpx.length_3d() / 1000  # Convertir a kilómetros
            return distance

    def calculate_days_since_start(date_str):
        start_date = datetime(2025, 11, 23)
        current_date = datetime.strptime(date_str, "%Y-%m-%d")
        return (current_date - start_date).days + 1

    def update_csv(file_name, distance, date_str, strava_url):
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
    
        # Calcular el número de días
        day = calculate_days_since_start(date_str)
    
        # Escribir la nueva fila en el archivo CSV
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([stage, day, date_str, distance, file_name])

   
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
        
        update_csv(str(filename)+".gpx", new_distance, date_of_route, strava_activity_url)
        
if __name__ == '__main__':
    asyncio.run(main()) 
