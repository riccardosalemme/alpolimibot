# Permette di ottenere gli UUID delle biblioteche di interesse.

import requests

# set cookie 0f18e8f356e34b64

# headers = {
#     'accept-language': 'en',
#     'authorization': 'c0b5b1c5-4bc5-463d-9e4c-06097768c82c',
#     'content-type': 'application/json',
#     'host': 'api.affluences.com',
#     'user-agent': 'Affluences/202603090 (Android; 15; M2007J20CG)',
#     'x-app-version': '202603090',
#     'x-device-type': 'android',
#     'x-service-name': 'mobile_app',
# }

headers = {
    'accept-language': 'en',
    'content-type': 'application/json',
    'host': 'api.affluences.com',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:150.0) Gecko/20100101 Firefox/150.0',
}

def search(query):
    params = {
        'q': query,
    }
    response = requests.get('https://api.affluences.com/app/v3/sites/search', params=params, headers=headers)
    response.raise_for_status()
    return response.json()

def live(site_id):
    response = requests.get(f'https://api.affluences.com/app/v4/sites/{site_id}/live-data', headers=headers)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    
    
    
    # live_data = live_data('334eec6e-69c5-4ef8-b645-5f3085009fb5')
    
    # is_open = live_data.get('data', {}).get('status', {}).get('isOpen')
    # live_occupancy = live_data.get('data', {}).get('liveAttendance', {}).get('occupancy')

    # print(f'Is open: {is_open}')
    # print(f'Live occupancy: {live_occupancy}')

    # exit(0)
    
    
    biblioteche = []

    results = search('Politecnico di Milano')
    for site in results.get('data', {}).get('sites', []):
        id = site.get('id')
        slug = site.get('slug')
        name = site.get('name')
        
        # print(f'{id} - {slug} - {name}')
        
        if 'Politecnico di Milano' in name:
            biblioteche.append({
                'id': id,
                'name': name,
                'slug': slug
            })
        
    with open('biblioteche.json', 'w') as f:
        import json
        json.dump(biblioteche, f, indent=4)
        
    for b in biblioteche:
        id = b.get('id')
        name = b.get('name')
        # print(f'Biblioteca: {name} - ID: {id}')
        live_data = live(id)
        
        
        is_open = live_data.get('data', {}).get('status', {}).get('isOpen')
        live_attendance = live_data.get('data', {}).get('liveAttendance', {})
        if live_attendance:
            live_occupancy = live_attendance.get('occupancy', None)
        else:
            live_occupancy = None

        print(f"{name} - Is open: {is_open} - Live occupancy: {live_occupancy}")
    
    
    



