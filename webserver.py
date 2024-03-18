from functools import cached_property #almacena una prodiedad en caché tras calcularlo una vez
from http.cookies import SimpleCookie #creación y manejo de cookies HTTP
import re #librería de expresiones regulares
#manejar solicutudes tipo HTTP de un servidor
#crear un servidor HTTP, para escuchar y manejar las solicitudes entrantes
from http.server import BaseHTTPRequestHandler, HTTPServer 
#analizar las cadenas de consulta
#analizar los componentes de los URL
from urllib.parse import parse_qsl, urlparse 
import redis #conexión con base de datos REDIS
import uuid #manipula los UUID - identificadores únicos universales
import os #comuincación con el sistema operativo
import urllib.parse #división y creación de URL en base a los componentes

#--------------------------------------------------------------------------#
# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html
#--------------------------------------------------------------------------#

#Conexión local con REDIS
r = redis.Redis(host="localhost", port = 6379, db = 0)

# definición de tuplas de mapeo, patrón de URL y llamada a la función 
# ^ coincide con el comienzo de la cadena $ final de la cadena
# ?P<> valida la referencia de la cadena de acuerdo al identificador
# \d+ coindide con un número con decimales
mappings = [
    (r"^/books/(?P<book_id>\d+)$","get_book"),
    (r"^/book/(?P<book_id>\d+)$","get_book"),
    (r"^/$","index"),
    (r"^/search$","search"),
           ]

#declaración de clase, hereda las propiedades del módulo BaseHTTPRequestHandler
class WebRequestHandler(BaseHTTPRequestHandler):
    
    #declaración de función para las solicitudes de búsqueda 
    def search(self):
        #verificación que se haya mandado una búsqueda 
        #'q' es donde se almacena la consulta de búsqueda
        if self.query_data and 'q' in self.query_data:
            query = self.query_data['q'] #asignar contenido de consulta 
            #busca en redis las palabras de manera indivual 'split'
            #sinter: devuelve los miembros del conjunto resultante de la intersección dada
            booksB = r.sinter(query.split(' ')) #busca los libros que tengan las palabras de la consulta
            lista = [] #declaración de lista
            #iteración para crear una lista de libros encontrados
            for b in booksB:
                y = b.decode() #decodificar la cadena
                lista.append(y) #agregar a lista
                print(lista) #imprimir lista (consola)
            #mostrar resultados de búsqueda de libros
            for i in range(0, len(lista)):
                if i<len(lista):
                    self.get_book(lista[i]) 
                else:
                    self.index()            
        #respuesta HTTP 
        self.send_response(200) #estado de éxito
        self.send_header('Content-type', 'text/html') #cabeceras de contenido
        self.end_headers()
   
    @property #definir a la función como propiedad de la clase
    #self: objeto de la clase
    def query_data(self):
        #devuelve los parametros de la cadena URL de consulta en un diccionario
        return dict(parse_qsl(self.url.query)) 
     
    @property  
    def url(self):
        #divide el URL devuelve y devuelve un objeto con el resultado
        return urlparse(self.path)
   
    def get_method(self, path):
        #iteración de la ruta y el metodo en mappings
        for pattern, method in mappings:
            #valida la ruta con la expresión regular 
            match = re.match(pattern, path)
            if match:
                #devuelve el metodo y un diccionario de rutas coincidentes
                return (method, match.groupdict())

    def get_recomendation(self,session_id,book_id):
        #insertar los valores a la lista (redis)
        r.rpush(session_id,book_id)
        #devolver los elementos especificados almacenados en keys (redis)
        books = r.lrange(session_id,0 ,-1)
        print(session_id,books) #imprime resultados
        
        #creacion de lista de enumeración de los libros 
        library = [str(i+1) for i in range(6)]
        #
        recomendation = [book for book in library if book not in
                        [read.decode() for read in books]]
        
        if len(recomendation) > 3:  # condición a > 3 para que recomiende después del segundo
            return recomendation[2]  # se devuelve el tercer libro de la lista de recomendaciones
        elif len(recomendation) > 0:
            return recomendation[0] #devuelve el primer libro de la lista de recomendaciones
        else:
            return "No hay recomendaciones"
   
    def get_book(self, book_id):
        session_id = self.get_session() #obtiene el session_id llamando al la función get_session
        get_recomendation = self.get_recomendation(session_id, book_id) #obtiene el la recomendació llamando al la función get_recomendation
        Indice = r.get(book_id) #drea una pagina con el libro de acuerdo al book_id obtenido de redis
        if Indice:
            #despliegue de la pagina
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.write_session_cookie(session_id) #escribe las cookies de la sesión
            self.end_headers()
            #despliegue de datos de sesión y recomendaciones
            response = f"""
            {Indice.decode()}
            <p>  Id-session: {session_id} </p>
            <p>  Te recomendamos leer: {get_recomendation} </p>
            """
            self.wfile.write(response.encode("utf-8"))
        else:
            self.send_error(404, "Not Found") #mensaje de error en caso de que no exista libro
     
    #función para tomar las cookies de las cabeceras de HTTP   
    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))
   
    def get_session(self):
        cookies = self.cookies() #obtener las cookies 
        session_id = None #inicializacion de la variable
        if not cookies:
            print("No existe cookie")
            cookies = SimpleCookie()
            session_id = uuid.uuid4() #genera un identificador aleatorio
        else:
            session_id = cookies["session_id"].value #obtiene el valor de la cookie ya registrado
        return session_id #devuelve el identificador
     
    #establecer cookies a la sesión actual   
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie() #crea un objeto del tipo SimpleCookie
        cookies["session_id"] = session_id #estable la cookie a la sesión actual
        cookies["session_id"]["max-age"] = 1000 #tiempo de expiración de la cookie
        self.send_header("Set-Cookie", cookies.output(header="")) #envia la cookie como header

    #manejo de solicitudes HTTP GET
    #funcion GET que solicita al servidor que te de la informacion al abrir el navegador 
    #obtiene el metodo que se esta solictando, tomando el path de la URL como argumento
    #obtiene el nombre del metodo y lo llama pasando los parametros del diccionario. 
    def do_GET(self):
        method = self.get_method(self.url.path)
        if method:  # Verifica si encuentra el metodo
            method_name, dict_params = method
            method = getattr(self, method_name)
            method(**dict_params) # ** = expande los argumentos del diccionario
            return
        else:
            # si no se encontro ningun metodo, el servidor manda error 404
            self.send_error(404, "Not Found")
            
       
    def index(self):
        session_id = self.get_session() #obtener el session_id llamando a la función get_session
        self.send_response(200) #respuesta HTTP
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id) #llama a la función write_session_cookie y le pasa el session_id
        self.end_headers()
        #abre el archivo index.html
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))


if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler) #comunicación con IP y puerto 8000
    server.serve_forever()
