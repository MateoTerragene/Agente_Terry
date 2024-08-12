from bs4 import BeautifulSoup
import requests 

def get_ifu_file(self):
        document_type = self.state.get("documento")
        product = self.state.get("producto")
        lote = self.state.get("lote")
        print(f"document_type: {document_type}, product: {product}")

        best_match_product = self.best_match(product, self.products_string)
        if not document_type or not product:
            print("no product or no type")
            return None
        base_url = "https://terragene.com/wp-content/uploads"
        subfolders = ["biologico", "electronica", "lavado", "quimico"]

        for subfolder in subfolders:
            url = f"{base_url}/{document_type}/{subfolder}/{product}/"
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        href = link.get('href')
                        if href and href.endswith('.pdf'):
                            if lote:
                                if href.lower().find(lote.lower()) != -1:
                                    return str(url + href)
                            else:
                                return str(url + href)
            except requests.RequestException as e:
                print(f"Error al acceder a {url}: {e}")

        return None