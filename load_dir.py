import os
import re
import redis
#permite interactuar con elementos de una pagina web
from bs4 import BeautifulSoup #extrae info en formato html/xml

#conexión tipo locar con la base de datos redis
r = redis.StrictRedis(host='localhost', port=6379, db=0)

#carga los libros (.html) en redis, y utiliza el ID como key
#directorio del html
def load_dir(path): 
    files = os.listdir(path) #lista de archivos del diccionario
    print(files)
    for f in files:
        match = re.match(r"^book(\d+).html$", f) #verifica el patrón de la ruta especificada con la expresión regular
        if match is not None:
            with open(path + f) as file: #abre el archivo html
                html = file.read() #lee el archivo
                book_id = match.group(1) #asigna el valor de su identificador
                create_index(book_id, html) #llama al metodo create_index y le pasa los parametros
                r.set(book_id, html) #almacena estable el valor de ID como clave en redis 
            print(f"{file} loaded into Redis") #mensaje de confirmación de la carga de libros

#ini=dice de palabras de los html (libros)
def create_index(book_id, html):
    soup = BeautifulSoup(html, 'html.parser') #crea un objeto que contiene la estructura del html
    ts = str(soup.p).lower() #obtiene el contenido de <p></p> y lo convierte a minúsculas
    palas = ts.split() #divide las palabras por espacios 
    for t in palas:
        t = t.replace(",","") #reemplaza/borra las comas del final de la palabra
        r.sadd(t,book_id) #agrega el identificador y añade la claves al índice de mapeo
    
#ejecución del método para cargar los html (libros)
load_dir('html/books/')