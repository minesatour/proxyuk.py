import requests
from bs4 import BeautifulSoup
from sklearn.neighbors import KNeighborsClassifier
import time

# List of proxy providers to scrape from
PROXY_SOURCES = [
    'https://www.sslproxies.org/',  # Original provider
    'https://www.free-proxy-list.net/',  # Alternative provider 1
    'https://www.us-proxy.org/',  # Alternative provider 2
    'https://www.proxy-list.download/',  # Alternative provider 3
]

# Function to fetch proxies from a proxy list website
def fetch_proxies():
    proxy_list = []
    
    for url in PROXY_SOURCES:
        print(f"Fetching proxies from {url}...")
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Check if the proxy table is available
            if 'sslproxies.org' in url:
                table = soup.find('table', {'id': 'proxylisttable'})
            elif 'free-proxy-list.net' in url:
                table = soup.find('table', {'id': 'proxylisttable'})
            elif 'us-proxy.org' in url:
                table = soup.find('table', {'id': 'proxylisttable'})
            elif 'proxy-list.download' in url:
                table = soup.find('table', {'class': 'table table-striped table-bordered'})

            if table is None:
                raise ValueError(f"Could not find proxy table on {url}.")
            
            rows = table.find_all('tr')[1:]  # Skipping the header row
            for row in rows:
                columns = row.find_all('td')
                if len(columns) > 0:
                    ip = columns[0].text.strip()
                    port = columns[1].text.strip()
                    proxy_list.append(f'{ip}:{port}')
        
        except Exception as e:
            print(f"Error fetching proxies from {url}: {e}")
    
    return proxy_list

# Function to test proxy speed
def test_proxy_speed(proxy):
    test_url = 'https://httpbin.org/ip'
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    try:
        start_time = time.time()
        response = requests.get(test_url, proxies=proxies, timeout=5)
        end_time = time.time()
        if response.status_code == 200:
            return end_time - start_time
    except requests.RequestException:
        return float('inf')  # Return a large number for unreachable proxies

    return float('inf')

# Function to classify proxies based on speed
def classify_proxies(proxies):
    if not proxies:
        print("No proxies available to classify.")
        return None, []

    speeds = []
    labels = []
    proxy_data = []
    
    for proxy in proxies:
        speed = test_proxy_speed(proxy)
        speeds.append(speed)
        proxy_data.append([speed])  # Using speed as the feature
    
    # Label proxies as 'fast' or 'slow' based on speed threshold
    threshold = 2  # Threshold in seconds
    labels = ['fast' if speed < threshold else 'slow' for speed in speeds]
    
    # Train the classifier
    classifier = KNeighborsClassifier(n_neighbors=3)
    X = proxy_data
    y = labels
    
    classifier.fit(X, y)
    
    return classifier, proxies

# Function to allow the user to select a proxy
def select_proxy_from_city(proxy_list, classifier):
    city = input("Enter the city for the proxy: ").lower()
    city_proxies = [proxy for proxy in proxy_list if city in proxy]
    
    if not city_proxies:
        print("No proxies found for that city.")
        return None
    
    # Classify proxies based on their speed
    proxy_data = []
    for proxy in city_proxies:
        speed = test_proxy_speed(proxy)
        proxy_data.append([speed])
    
    predictions = classifier.predict(proxy_data)
    
    for proxy, prediction in zip(city_proxies, predictions):
        print(f"Proxy: {proxy}, Speed: {'Fast' if prediction == 'fast' else 'Slow'}")
    
    selected_proxy = input("Enter the proxy to connect to (e.g., '192.168.1.1:8080'): ")
    
    if selected_proxy not in city_proxies:
        print("Invalid proxy selection.")
        return None
    
    return selected_proxy

# Function to connect to the selected proxy
def connect_to_proxy(proxy):
    proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    try:
        response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=5)
        if response.status_code == 200:
            print(f"Successfully connected to proxy {proxy}")
            return True
    except requests.RequestException:
        print(f"Failed to connect to proxy {proxy}")
        return False

# Main function to run the proxy selection process
def run_proxy_selection():
    print("Fetching proxies...")
    proxies = fetch_proxies()
    
    if not proxies:
        print("No proxies fetched. Exiting.")
        return
    
    print(f"Fetched {len(proxies)} proxies.")
    
    print("Classifying proxies based on speed...")
    classifier, proxy_list = classify_proxies(proxies)
    
    if classifier is None:
        print("No proxies to classify.")
        return
    
    print("Select a proxy by entering the city name.")
    selected_proxy = select_proxy_from_city(proxy_list, classifier)
    
    if selected_proxy:
        print(f"Connecting to proxy {selected_proxy}...")
        if connect_to_proxy(selected_proxy):
            print(f"Successfully connected to {selected_proxy}.")
        else:
            print("Connection failed.")

if __name__ == "__main__":
    run_proxy_selection()
