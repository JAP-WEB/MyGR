from functools import cached_property
from http.cookies import SimpleCookie
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import redis
import uuid
import os
import urllib.parse

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html

r = redis.Redis(host="localhost", port = 6379, db = 0)


mappings = [
    (r"^/books/(?P<book_id>\d+)$","get_book"),
    (r"^/book/(?P<book_id>\d+)$","get_book"),
    (r"^/$","index"),
    (r"^/search$","search"),
           ]

class WebRequestHandler(BaseHTTPRequestHandler):
    def search(self):
        if self.query_data and 'q' in self.query_data:
            query = self.query_data['q']
            booksB = r.sinter(query.split(' '))
            lista = []
            for b in booksB:
                y = b.decode()
                lista.append(y)
                print(lista)
            for i in range(0, len(lista)):
                if i<len(lista):
                    self.get_book(lista[i])
                else:
                    self.index()            

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    
    @property
    def query_data(self):
        return dict(parse_qsl(self.url.query))
     
    @property  
    def url(self):
        return urlparse(self.path)
    
    def get_method(self, path):
        for pattern, method in mappings:
            match = re.match(pattern, path)
            if match:
                return (method, match.groupdict())
    
    def get_recomendation(self,session_id,book_id):
        r.rpush(session_id,book_id)
        books = r.lrange(session_id,0 ,6)
        print(session_id,books)
        
        library = [str(i+1) for i in range(6)]
        recomendation = [book for book in library if book not in
                        [read.decode() for read in books]]
        
        if len(recomendation) > 3:  # Cambiamos la condición a > 3 para que recomiende después del segundo
            return recomendation[2]  # Devolvemos el tercer libro de la lista de recomendaciones
        elif len(recomendation) > 0:
            return recomendation[0]
        else:
            return "No te puedo recomendar nada"

    
    def get_book(self, book_id):
        session_id = self.get_session()
        get_recomendation = self.get_recomendation(session_id, book_id)
        Indice = r.get(book_id)
        if Indice:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.write_session_cookie(session_id)
            self.end_headers()
            response = f"""
            {Indice.decode()}
        <p>  Id-session: {session_id}      </p>
        <p>  Te recomendamos leer: {get_recomendation}    </p>
"""
            self.wfile.write(response.encode("utf-8"))
        else:
            self.send_error(404, "Not Found")
        
    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))
    
    def get_session(self):
        cookies = self.cookies()
        session_id = None
        if not cookies:
            print("No existe cookie")
            cookies = SimpleCookie()
            session_id = uuid.uuid4()
        else:
            session_id = cookies["session_id"].value
        return session_id
        
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max-age"] = 1000
        self.send_header("Set-Cookie", cookies.output(header=""))
    
    def do_GET(self):
        method = self.get_method(self.url.path)
        if method:
            method_name, dict_params = method
            method = getattr(self, method_name)
            method(**dict_params)
            return
        else:
            self.send_error(404, "Not Found")

        
    def index(self):
        session_id = self.get_session()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))


if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()
    