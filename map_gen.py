import folium
from geopy import distance

tooltip = "Нажми на меня!"


def generate_map(info, check_rad=False, center_lat=0, center_lon=0, radius=0):
    print(info)
    not_in_circle = []
    in_circle = []
    m = folium.Map(location=["private_x", "private_y"], zoom_start=20, tiles="OpenStreetMap")
    center_coords = 0
    if check_rad:
        center_coords = (center_lat, center_lon)
    for pos in info:
        color = 'green'
        if check_rad:
            point_coords = (pos[0], pos[1])
            dist = distance.distance(center_coords, point_coords).meters
            if dist > radius:
                color = 'gray'
                not_in_circle.append(pos[2])
            else:
                in_circle.append(pos[2])
        print(pos)
        folium.Marker(
            [pos[0], pos[1]], popup="<i>{}</i>".format(pos[2] + " " + pos[3]), tooltip=tooltip,
            icon=folium.Icon(color=color)
        ).add_to(m)
    name = 'map.html'
    m.save(name)
    return name, not_in_circle, in_circle


