from strava2gpx import strava2gpx
from stravalib import Client
from datetime import datetime
import requests
import base64
import os
import asyncio

async def main():
    '''
    put in your Strava Api client_id, refresh_token, and client_secret
    '''
    client_id = os.getenv('STRAVA_CLIENT_ID')
    print (client_id)
    refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')

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

if __name__ == '__main__':
    asyncio.run(main()) 
