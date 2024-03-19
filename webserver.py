from functools import cached_property #almacena una prodiedad en caché tras calcularlo una vez
from http.cookies import SimpleCookie #creación y manejo de cookies HTTP
import re #librería de expresiones regulares
#manejar solicutudes tipo HTTP de un servidor
#crear un servidor HTTP para escuchar y manejar las solicitudes entrantes
from http.server import BaseHTTPRequestHandler, HTTPServer 
#analizar las cadenas de consulta
#analizar los componentes de los URL
from urllib.parse import parse_qsl, urlparse 
import redis #conexión con base de datos redis
import uuid #manipula los UUID - identificadores únicos universales
import os #comuincación con el sistema operativo
import urllib.parse #división y creación de URL en base a los componentes

#--------------------------------------------------------------------------#
# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html
#--------------------------------------------------------------------------#

#establecer conexión tipo local con la base de datos Redis
#db especifica el número de base de datos en la cual se hará la conexión
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
    
    #declaración de método para las solicitudes de búsqueda 
    def search(self):
        #verificación que se haya mandado una búsqueda 
        #'q' es donde se almacena la consulta de búsqueda
        if self.query_data and 'q' in self.query_data:
            query = self.query_data['q'] #asignar contenido de consulta 
            #busca en redis las palabras de manera indivual 'split'
            #sinter: devuelve los miembros del conjunto resultante de la intersección dada
            books = r.sinter(query.split(' ')) #busca los libros que tengan las palabras de la consulta
            lista_libros = [] #declaración de lista
            #iteración para crear una lista de libros encontrados
            for b in books:
                cadena = b.decode() #decodificar la cadena
                lista_libros.append(cadena) #agregar a lista
                print(lista_libros) #imprimir lista (consola)
            #mostrar resultados de búsqueda de libros
            for i in range(0, len(lista_libros)):
                if i<len(lista_libros):
                    self.get_book(lista_libros[i]) 
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
        #divide el URL y devuelve un objeto con el resultado
        return urlparse(self.path)
   
    def get_method(self, path):
        #iteración de la ruta y el método en mappings
        for pattern, method in mappings:
            #valida la ruta con la expresión regular 
            match = re.match(pattern, path)
            if match:
                #devuelve el método y un diccionario de rutas coincidentes
                return (method, match.groupdict())
   
   #obtiene lista de libros asociados a la sesion, limitando el rango de libros
    def get_recomendation(self,session_id,book_id):
        r.rpush(session_id,book_id)
        books = r.lrange(session_id,0 ,6)
        print(session_id,books)
        library = [str(i+1) for i in range(6)] # crea etiquetas de libros (str-cadenas)
        
        # crea lista de recs, revisa los libros leidos, sino los agrega a lista de recs
        recomendation = [book for book in library if book not in
                        [read.decode() for read in books]]
        
        # Recomienda despues del segundo libro, devolviendo la rec del 3
        if len(recomendation) > 3:  
            return recomendation[2] 
        # Si hay al menos 1 libro en recs, devolver el 1er libro de la lista
        elif len(recomendation) > 0:
            return recomendation[0]
        else:
            return "No hay recomendaciones" # No quedan libros en la lista
   
    def get_book(self, book_id):
        session_id = self.get_session() #obtiene el session_id llamando al método get_session
        get_recomendation = self.get_recomendation(session_id, book_id) #obtiene la recomendación llamando al método get_recomendation
        pagina = r.get(book_id) #crea una página con el libro de acuerdo al book_id obtenido de redis
        if pagina:
            #despliegue de la página
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.write_session_cookie(session_id) #escribe las cookies de la sesión
            self.end_headers()
            #despliegue de datos de sesión y recomendaciones
            response = f"""
            {pagina.decode()}
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
        cookies["session_id"] = session_id #establece la cookie a la sesión actual
        cookies["session_id"]["max-age"] = 1000 #tiempo de expiración de la cookie
        self.send_header("Set-Cookie", cookies.output(header="")) #envía la cookie como header
   
    #manejo de solicitudes HTTP GET
    def do_GET(self):
        method = self.get_method(self.url.path)
        if method:  #verifica si encuentra el metodo
            method_name, dict_params = method
            method = getattr(self, method_name)
            method(**dict_params) # ** = expande los argumentos del diccionario
            return
        else:
            #si no se encontro ningun metodo, el servidor manda error 404
            self.send_error(404, "Not Found")
            
            
    def index(self):
        session_id = self.get_session() #obtener el session_id llamando al método get_session
        self.send_response(200) #respuesta HTTP
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id) #llama al método write_session_cookie y le pasa el session_id
        self.end_headers()
        #abre el archivo index.html
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))


if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler) #comunicación con IP y puerto 8000
    server.serve_forever()
