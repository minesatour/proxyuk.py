import requests
from bs4 import BeautifulSoup
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import time
import logging
from requests.exceptions import RequestException

# Setup logging
logging.basicConfig(filename="proxy_selector.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


# Function to fetch and classify proxies based on geolocation
def ip_to_features(ip):
    """Converts the IP address into numeric features (simplified)."""
    return [int(ip.split('.')[0]), int(ip.split('.')[1])]  # Simple feature based on IP address


def get_proxy_location(ip):
    """Use multiple geolocation APIs to determine the city or town of the proxy."""
    try:
        # First, try ipinfo.io
        response = requests.get(f"http://ipinfo.io/{ip}/json")
        data = response.json()
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")
        logging.info(f"Geolocation lookup for {ip} via ipinfo.io: {city}, {country}")
        return city
    except RequestException as e:
        logging.error(f"Error with ipinfo.io for IP {ip}: {e}")
    
    try:
        # Fallback to ip-api.com
        response = requests.get(f"http://ip-api.com/json/{ip}")
        data = response.json()
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")
        logging.info(f"Geolocation lookup for {ip} via ip-api.com: {city}, {country}")
        return city
    except RequestException as e:
        logging.error(f"Error with ip-api.com for IP {ip}: {e}")
    
    return "Unknown"  # Fallback if both APIs fail


def fetch_and_classify_proxies():
    """Fetch proxies from a public proxy site and classify them into towns/cities."""
    url = "https://www.freeproxylists.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    proxy_list = []
    
    for row in soup.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) > 0:
            ip = cols[0].text.strip()
            country = cols[3].text.strip()
            if country == "United Kingdom":
                proxy_list.append(f"{ip}:8080")  # Assume port 8080 for simplicity
    
    # Use geolocation API to classify proxies by location (town/city)
    classified_proxies = []
    for proxy in proxy_list:
        ip = proxy.split(":")[0]  # Get the IP address
        city = get_proxy_location(ip)  # Get the city from the geolocation API
        classified_proxies.append({"ip": proxy, "city": city})
    
    # For simplicity, classify proxies using a basic model (in practice, use real data/features)
    X = np.array([ip_to_features(proxy["ip"]) for proxy in classified_proxies])
    y = np.array([proxy["city"] for proxy in classified_proxies])
    
    classifier = KNeighborsClassifier(n_neighbors=1)
    classifier.fit(X, y)

    return classifier, classified_proxies


def search_proxy(proxies, city):
    """Search for proxies that match the given city."""
    return [proxy for proxy in proxies if city.lower() in proxy["city"].lower()]


def test_proxy_speed(proxy_address):
    """Test the speed of the proxy by making a request and measuring the response time."""
    proxies = {
        "http": f"http://{proxy_address}",
        "https": f"http://{proxy_address}"
    }

    try:
        start_time = time.time()
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=5)
        end_time = time.time()
        response_time = end_time - start_time
        logging.info(f"Proxy {proxy_address} speed test: {response_time:.2f} seconds")
        return response_time
    except RequestException as e:
        logging.error(f"Error testing proxy {proxy_address}: {e}")
        return float('inf')  # Return infinite time if the proxy fails


def set_proxy(proxy_address, username=None, password=None):
    """Set the system proxy to the selected proxy with optional authentication."""
    proxies = {
        "http": f"http://{proxy_address}",
        "https": f"http://{proxy_address}"
    }

    # Add authentication if provided
    if username and password:
        proxies["http"] = f"http://{username}:{password}@{proxy_address}"
        proxies["https"] = f"https://{username}:{password}@{proxy_address}"

    try:
        # Test the proxy by making a request
        response = requests.get('http://httpbin.org/ip', proxies=proxies)
        print(f"Connected via proxy: {proxy_address}")
        print(f"Your IP is: {response.json()['origin']}")
        logging.info(f"Successfully connected to {proxy_address}")
    except RequestException as e:
        print(f"Error: Unable to connect via proxy {proxy_address}")
        logging.error(f"Failed to connect via {proxy_address}: {e}")


def run_proxy_selection():
    """Main function to fetch proxies, classify, and allow the user to select one."""
    classifier, proxy_list = fetch_and_classify_proxies()  # Fetch and classify proxies

    while True:
        city = input("Enter the city (e.g., London): ").strip()
        
        available_proxies = search_proxy(proxy_list, city)
        if available_proxies:
            print(f"Found {len(available_proxies)} proxies for {city}:")
            
            # Sort proxies by speed (ascending order, faster proxies first)
            available_proxies.sort(key=lambda proxy: test_proxy_speed(proxy["ip"]))
            
            for i, proxy in enumerate(available_proxies, 1):
                print(f"{i}. {proxy['ip']} - Speed: {test_proxy_speed(proxy['ip']):.2f}s")
            
            try:
                choice = int(input(f"Choose a proxy (1-{len(available_proxies)}): "))
                chosen_proxy = available_proxies[choice - 1]
                authentication = input("Does the proxy require authentication? (yes/no): ").strip().lower()
                
                if authentication == "yes":
                    username = input("Enter username: ").strip()
                    password = input("Enter password: ").strip()
                    set_proxy(chosen_proxy['ip'], username, password)
                else:
                    set_proxy(chosen_proxy['ip'])
                break  # Exit the loop after successful connection
            except ValueError:
                print("Invalid choice. Please choose a number from the list.")
            except IndexError:
                print("Invalid number. Please choose a valid proxy from the list.")
        else:
            print(f"No proxies found for {city}. Try again.")


def update_proxy_list():
    """Automatically update the proxy list and classifier every 5 minutes."""
    while True:
        print("Fetching and classifying proxies...")
        classifier, proxy_list = fetch_and_classify_proxies()  # Fetch and classify proxies
        print(f"Found {len(proxy_list)} proxies.")
        time.sleep(300)  # Wait for 5 minutes before updating again


if __name__ == "__main__":
    # Start the proxy selection process
    try:
        run_proxy_selection()
    except KeyboardInterrupt:
        print("\nExiting program...")
        logging.info("Program exited by user.")
    
    # Uncomment the line below to run the automatic update process in the background (optional)
    # update_proxy_list()  # This will update proxies every 5 minutes
