import os
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from .models import Book

from bs4 import BeautifulSoup

def home(request):
    books = Book.objects.all()
    return render(request, 'home.html', {'books': books})

def scrape(request):
    # Configuración del driver de Selenium
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Ejecutar en segundo plano
    driver = webdriver.Chrome(options=options)

    # Visitar la página principal de Freeditorial
    driver.get("https://freeditorial.com/")

    # Esperar a que se cargue la página y aceptar las cookies
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "cookiebanner"))
    )
    driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar')]").click()

    # Obtener las tarjetas de los libros en la sección de Novedades
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    cards = soup.find_all('div', {'class': 'card'})

    # Recorrer las tarjetas de los libros
    for card in cards:
        title = card.find('h5', {'class': 'card-title'}).text.strip()
        author = card.find('h6', {'class': 'card-subtitle'}).text.strip()
        free = card.find('span', {'class': 'free'})
        if free is not None and author == 'Arik Eindrok':
            # Acceder al detalle del libro
            link = card.find('a', href=True)['href']
            driver.get(link)

            # Descargar el PDF del libro
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'PDF')]"))
            )
            driver.find_element(By.XPATH, "//a[contains(text(), 'PDF')]").click()

            # Almacenar el archivo PDF en una carpeta interna
            with open(f'books/{title}.pdf', 'wb') as f:
                f.write(driver.find_element(By.XPATH, "//embed").get_attribute("src"))

            # Guardar el libro en la base de datos
            book = Book(title=title, author=author)
            book.save()

    # Cerrar el driver de Selenium
    driver.quit()

    return HttpResponse("El web scraping se ha completado exitosamente.")


def book_list(request):
    books = Book.objects.all()
    return render(request, 'book_list.html', {'books': books})

def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'book_detail.html', {'book': book})

def download_books(request):
    # Inicializamos el driver de Selenium
    options = webdriver.ChromeOptions()
    options.add_argument('headless') # Para que no abra una ventana del navegador
    driver = webdriver.Chrome(options=options)

    # Navegamos hasta la página de Freeditorial
    driver.get('https://freeditorial.com/')
    time.sleep(5)

    # Hacemos clic en el botón "Libros Gratis"
    driver.find_element_by_link_text('Libros Gratis').click()
    time.sleep(5)

    # Obtenemos la lista de libros
    books = driver.find_elements_by_css_selector('.card')
    for book in books:
        # Obtenemos el título del libro y comprobamos si es de Arik Eindrok y es gratuito
        title = book.find_element_by_css_selector('.title').text
        author = book.find_element_by_css_selector('.author').text
        price = book.find_element_by_css_selector('.price').text
        if 'Arik Eindrok' in author and 'Gratis' in price:
            # Hacemos clic en el botón "PDF" para descargar el libro
            book.find_element_by_link_text('PDF').click()
            time.sleep(5)

            # Guardamos el archivo PDF en una carpeta llamada "books" dentro de la carpeta media
            filename = f"{title}.pdf"
            filepath = os.path.join('media', 'books', filename)
            with open(filepath, 'wb') as f:
                f.write(driver.find_element_by_tag_name('body').screenshot_as_pdf)

    # Cerramos el driver de Selenium
    driver.quit()

    # Redirigimos a la página de lista de libros
    return redirect('book_list')

def home(request):
    books = Book.objects.all()
    return render(request, 'home.html', {'books': books})

def download_book(request, pk):
    # Obtener el objeto Book correspondiente al ID de la URL
    book = get_object_or_404(Book, pk=pk)

    # Configuración de Selenium para descargar el PDF
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.get(book.url)
    pdf_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "PDF")]')))
    pdf_button.click()
    driver.quit()

    # Preparar la respuesta HTTP con el archivo PDF descargado
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{book.title}.pdf"'
    with open(f'{book.title}.pdf', 'rb') as f:
        response.write(f.read())

    return response


def scrape_books(request):
    # Configuración de Selenium para el web scraping
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.get("https://freeditorial.com/novedades")

    # Obtener los elementos HTML de los libros gratuitos
    free_books = driver.find_elements_by_xpath('//div[@class="book-card-details"]//a[@title="Descargar gratis"]/parent::*/preceding-sibling::div[@class="book-card-cover"]//a')

    # Descargar los PDF de los libros gratuitos
    for book in free_books:
        url = book.get_attribute('href')
        title = book.get_attribute('title')
        try:
            Book.objects.get(title=title, author="Arik Eindrok", url=url)
        except Book.DoesNotExist:
            # Si el libro no existe en la base de datos, lo creamos
            Book.objects.create(title=title, author="Arik Eindrok", url=url)
            # Descargamos el PDF del libro y lo almacenamos en la carpeta media
            driver.get(url)
            pdf_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "PDF")]')))
            pdf_button.click()
            with open(f'media/{title}.pdf', 'wb') as f:
                f.write(driver.find_element_by_css_selector('.pdf-reader embed').get_attribute('src').split('data:application/pdf;base64,')[1].encode())
            messages.success(request, f"Se descargó el PDF del libro {title}")
        else:
            messages.warning(request, f"El libro {title} ya fue descargado anteriormente")

    driver.quit()
    return redirect('home')