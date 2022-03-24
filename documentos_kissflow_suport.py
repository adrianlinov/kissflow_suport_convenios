import base64
import sys
import traceback
from numpy.core.fromnumeric import prod
from pandas.core.frame import DataFrame
import requests
from datetime import datetime, date, timedelta
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from tabulate import tabulate
import shutil
from termcolor import colored, cprint
import pandas as pd
import os
from os.path import isdir, isfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from docx import Document
from docx.shared import Inches
from docx2pdf import convert
import re
import logging
from zipfile import ZIP_DEFLATED, ZipFile, ZIP_STORED
import zlib
from time import sleep
import pdf2image

import bbdd



def fun(path, name):  # Function to convert file path into clickable form.
    return '<a href="{}">{}</a>'.format(path, name)


def fun(path, name):
    '''Function to convert file path into clickable form.'''
    # returns the final component of a url
    #f_url = os.path.basename(path)
    return '<a href="{}">{}</a>'.format(path, name)


logger.info("-" * 80)
logger.info(f"Inicio ejecucion documentos.py")

##### Conection to Kissflow API #####
n_pag = 1
account_id = "#"
key_api = "#"
total_pag = 100
headers = {"Accept": "*/*", "X-Api-Key": f"{key_api}"}
stop = False
today = datetime.now().date()
columnas = None
datos_enviar = []
datos_validar = []
while not stop:
    url = f"https://recsa.kissflow.com/process/2/{account_id}/admin/Documentos_convenios_Armony_PE/item/p{n_pag}/{total_pag}"
    response = requests.get(url, headers=headers)
    json_data = json.loads(response.text)
    data_json = json_data["Data"]
    if len(data_json) < total_pag:
        stop = True
    for data in data_json:
        fecha_entrevista = data['_created_at'].split('T')[0].split("-")
        fecha_entrevista = [int(f) for f in fecha_entrevista]
        fecha_entrevista = date(fecha_entrevista[0], fecha_entrevista[1],
                                fecha_entrevista[2])
        if fecha_entrevista < today - timedelta(days=20): 
            stop = True
            break
        else:
            # Get submitions that are in the fase 'Descarga Archivos' and 'Validacion Documentos'
            try:
                id = data['_id']
                url_det = f"https://recsa.kissflow.com/process/2/{account_id}/admin/Documentos_convenios_Armony_PE/{id}"
                response_det = requests.request("GET",
                                                url_det,
                                                headers=headers)
                json_detail = json.loads(response_det.text)
                if '_current_step' not in json_detail.keys():
                    pass
                elif json_detail['_current_step'] == 'Descarga Archivos':
                    datos_enviar.append(data)
                elif json_detail['_current_step'] == 'Validacion Documentos':
                    datos_validar.append(data)
            except Exception as e:
                logger.error(e)

    n_pag += 1
datos_enviar.reverse()
datos_validar.reverse()
print(len(datos_validar))


# If there are no submitions in the fase 'Descarga Archivos'
if len(datos_enviar) > 0:
    for data in datos_enviar: 
        dict_aux = bbdd.encontrar_convenio(data['Numero_DNI_1'])
        estado_base = 'Envio Convenio'
        # Search in database
        if len(dict_aux) == 0:
            estado_base = 'Revision Supervisor'
            dict_aux = bbdd.encontrar_convenio(data['Numero_DNI_1'],
                                               estado=estado_base)
        # If the submitions are correct in the databsae
        if len(dict_aux) > 0:
            logger.info(f"Dato a enviar existe en la BBDD")
            dict_aux = dict_aux[0]
            dni, ced, mail_ejecutivo = dict_aux['DNI'], dict_aux[
                'Cedente'], dict_aux['Mail Ejecutivo']
            aux_path = f'{dni}_{ced}'
            
            # If the client wants Life Insurance
            if (data["Desea_obtener_su_seguro_de_vida"] == True):
                try:
                    logger.info(f"Seguro de Vida: SI")
                    nombres_archivos = ['DNI_frontal', 'DNI_posterior', 'Recibo_de_Servicios']
                    dic_de_listas_de_urls = {'DNI_frontal' : [], 'DNI_posterior' : [], 'Recibo_de_Servicios':[]}
                    for nombre_archivo in nombres_archivos:
                        lista_de_documentos_adjuntados_de_nombre_archivo = data[f'{nombre_archivo}']
                        for i in range(len(lista_de_documentos_adjuntados_de_nombre_archivo)):
                            direccion = lista_de_documentos_adjuntados_de_nombre_archivo[i]['key']
                            url_de_descarga = f"https://recsa.kissflow.com/upload/2/{account_id}/{direccion}"
                            nombre_archivo_subido = url_de_descarga.split('/')[-1]
                            extension = nombre_archivo_subido.split(".")[-1]
                            headers_aux = {
                                "Accept": "*/*",
                                "X-Api-Key": f"{key_api}",
                            }
                            response = requests.get(url_de_descarga,
                                                        headers=headers_aux,
                                                        stream=True)
                            if not isdir(f'{DOCS}/{aux_path}'):
                                    os.makedirs(f'{DOCS}/{aux_path}')
                            if not isdir(f'{ARMONY_DOCS}/{aux_path}'):
                                os.makedirs(f'{ARMONY_DOCS}/{aux_path}')
                            if i == 0:
                                logger.info(f"{DOCS}/{aux_path}/{nombre_archivo}.{extension}")
                                extension_original = extension.lower()
                                if extension.lower() == "pdf":
                                    extension = "jpg"
                                
                                rutas_pdf = []
                                if extension_original.lower() == "pdf":
                                    images = pdf2image.convert_from_bytes(response.content)

                                    if len(images) == 0:
                                        ruta_aux = f"{DOCS}\{aux_path}\{nombre_archivo}.{extension}"
                                        logger.info(images[0].save(ruta_aux))
                                        rutas_pdf.append(ruta_aux)
                                    
                                    else:
                                        contador_imagenes = 1
                                        for image in images:
                                            ruta_aux = f"{DOCS}\{aux_path}\{nombre_archivo}_{contador_imagenes}.{extension}"
                                            rutas_pdf.append(ruta_aux)
                                            logger.info(image.save(ruta_aux)) 
                                            contador_imagenes = contador_imagenes + 1
                                    # output_file.write(output_file)
                                else:
                                    with open(f"{DOCS}\{aux_path}\{nombre_archivo}.{extension}",'wb') as output_file:
                                        output_file.write(response.content)

                                logger.info(f"RUTAS: {str(rutas_pdf)}")
                                for ruta in rutas_pdf:
                                    with open(ruta,'rb+') as output_file:
                                        data_post = {
                                            'key': "a2846d4c1cf92d715271807143a19345", 
                                            "image" : base64.b64encode(output_file.read())
                                        }
                                        upload_request = requests.post("https://api.imgbb.com/1/upload", data=data_post)
                                        logger.info(upload_request.text)
                                        url_de_archivo_cargado = str(upload_request.json()["data"]["url"])
                                        dic_de_listas_de_urls[nombre_archivo].append(url_de_archivo_cargado)


                             
                            else:
                                
                                extension_original = extension.lower()
                                if extension.lower() == "pdf":
                                    extension = "jpg"
                                
                                with open(f"{DOCS}/{aux_path}/{nombre_archivo}_{i}.{extension}",'wb') as output_file:
                                    if extension_original.lower() == "pdf":
                                        image = pdf2image.convert_from_bytes(response.content)[0]
                                        logger.info(image.save(f"{DOCS}/{aux_path}/{nombre_archivo}_{i}.{extension}"))
                                    else:
                                        output_file.write(response.content)

                                with open(f"{DOCS}/{aux_path}/{nombre_archivo}_{i}.{extension}",'rb+') as output_file:
                                    # output_file.write(response.content)
                                    data_post = {
                                        'key': "a2846d4c1cf92d715271807143a19345", 
                                        "image" : base64.b64encode(output_file.read())
                                    }
                                    upload_request = requests.post("https://api.imgbb.com/1/upload", data=data_post)
                                    logger.info(upload_request.text)
                                    url_de_archivo_cargado = str(upload_request.json()["data"]["url"])
                                    dic_de_listas_de_urls[nombre_archivo].append(url_de_archivo_cargado)





                    # * : RECUPERAR LAS RESPUESTAS DEL SEGURO Y ENVIARLAS A LA BASE DE DATOS JUNTO CON LOS URLS DE LOS ARCHIVOS
                    logger.info(data['Numero_DNI_1'])
                    logger.info(data)
                    logger.info(dic_de_listas_de_urls)
                    bbdd.actualizar_estado2(dni=data['Numero_DNI_1'], dic_respuestas=data, dic_de_listas_de_urls=dic_de_listas_de_urls, logger=logger)
                    # * : MAIL QUE SE ENVIA AL CLIENTE INFORMANDO QUE SE LE VA A GENERAR EL SEGURO
                    send_email(
                                "adrian.lino@recsa.com",
                                'Felicitaciones! Tu solicitud de Seguro de Vida ha sido enviada',
                                'Haz completado todos los pasos del proceso para obtener tu Seguro de Vida. En caso exista algun problema con los documentos un asesor se contactará contigo.',
                                )
                    

                    # * : SI NO QUIERE CARTA DE NO ADEUDO, HACER SUBMIT Y EN KISSFLOW HACER UN PUENTE PARA QUE SE CULMINE EL PROCESO 
                    if data["Quieres_obtener_tu_carta_de_no_adeudo"] == False:
                        id = data['_id']
                        a_id = data['_activity_instance_id'][0]
                        url = f"https://recsa.kissflow.com/process/2/{account_id}/Documentos_convenios_Armony_PE/{id}/{a_id}/submit"
                        headers = {"Accept": "*/*", "X-Api-Key": f"{key_api}"}
                        response = requests.request("POST", url, headers=headers)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error(f"{exc_type}, {fname}, {exc_tb.tb_lineno}")
                    logger.error(traceback.format_exc())
                    continue

            # If the client wants letter of no debt
            # The files are saved and send for review with the executive
            if data["Quieres_obtener_tu_carta_de_no_adeudo"] == True or data["Quieres_obtener_tu_carta_de_no_adeudo"] == None:
                try:
                    logger.info(f"Carta de No Adeudo: SI")
                    aux_path = f'{dni}_{ced}'
                    if not isdir(f'{DOCS}/{aux_path}'):
                        os.makedirs(f'{DOCS}/{aux_path}')
                    if not isdir(f'{ARMONY_DOCS}/{aux_path}'):
                        os.makedirs(f'{ARMONY_DOCS}/{aux_path}')
                    if isfile(f'{PDF}/{aux_path}.pdf'):
                        #Si es que existe un convenio generado asociado
                        #Copiamos el pdf a la carpeta respectiva
                        shutil.copy(f'{PDF}/{aux_path}.pdf',
                                    f'{DOCS}/{aux_path}/Convenio_Generado.pdf')
                        #Subimos el pdf a Kissflow
                        id = data['_id']
                        url_atch_file = f"https://recsa.kissflow.com/process/2/{account_id}/admin/Documentos_convenios_Armony_PE/{id}/Convenio_Generado/attachment"
                        logger.info(f"inicio pdf")
                        with open(f'{PDF}/{aux_path}.pdf', 'rb') as f:
                            multipart_data = MultipartEncoder(
                                fields={'file': ('Convenio_Generado.pdf', f)})
                            headers = {
                                "Accept": "*/*",
                                "X-Api-Key": f"{key_api}",
                                "Content-Type": multipart_data.content_type
                            }
                            response = requests.post(url_atch_file,
                                                    data=multipart_data.to_string(),
                                                    headers=headers)
                        logger.info(f"fin pdf")
                        # Descargamos imagenes de Kissflow
                        archivos = ['DNI_frontal', 'DNI_posterior', 'Convenio_Firmado']
                        adjuntos = [f'{DOCS}/{aux_path}/Convenio_Generado.pdf']
                        for a in archivos:
                            dni_frontal = data[f'{a}']
                            for i in range(len(dni_frontal)):
                                direccion = dni_frontal[i]['key']
                                url_aux = f"https://recsa.kissflow.com/upload/2/{account_id}/{direccion}"
                                nombre_archivo = url_aux.split('/')[-1]
                                extension = nombre_archivo.split(".")[-1]
                                headers_aux = {
                                    "Accept": "*/*",
                                    "X-Api-Key": f"{key_api}",
                                }
                                response_aux = requests.get(url_aux,
                                                            headers=headers_aux,
                                                            stream=True)
                                if i == 0:
                                    with open(f"{DOCS}/{aux_path}/{a}.{extension}",
                                                'wb') as output_file:
                                        output_file.write(response_aux.content)
                                    adjuntos.append(
                                        f"{DOCS}/{aux_path}/{a}.{extension}")
                                else:
                                    with open(
                                            f"{DOCS}/{aux_path}/{a}_{i}.{extension}",
                                            'wb') as output_file:
                                        output_file.write(response_aux.content)
                                    adjuntos.append(
                                        f"{DOCS}/{aux_path}/{a}_{i}.{extension}")
                        link_sharepoint = f'https://recsa.sharepoint.com/sites/CentrodeExcelenciaRPA/Documentos%20compartidos/Forms/AllItems.aspx?id=%2Fsites%2FCentrodeExcelenciaRPA%2FDocumentos%20compartidos%2FData%20Clientes%2FPeru%2FArmony%20PE%2FConvenios-CartaNoAdeudo%2FDOCS%2F{aux_path}'
                        #Enviamos el mail de aviso
                        send_email(
                            'adrian.lino@recsa.com',
                            f'Documentos Subidos por cliente {dict_aux["DNI"]}',
                            f'''El Cliente {dict_aux["Nombre Cliente"]}, de DNI {dict_aux["DNI"]} ha subido sus documentos.<br>
                                Revisa en Kissflow o en la carpeta respectiva de sharepoint ({fun(link_sharepoint, "<b> CLICK AQUÍ </b>")}) los archivos, y determina si debe aprobarse o no la información para la generación de la carta de no adeudo.<br>
                                La ID de la solicitud en Kissflow es {data["ID_Solicitud"]} (También puedes buscar por DNI del cliente)''',
                            )
                        
                        logger.info(
                            f"Mail aviso al ejecutivo para verificacion de documentos de carta de no adeudo"
                        )

                        for archivo in adjuntos:
                            if os.path.exists(
                                    f'{ARMONY_DOCS}/{aux_path}/{archivo.split("/")[-1]}'
                            ):
                                os.remove(
                                    f'{ARMONY_DOCS}/{aux_path}/{archivo.split("/")[-1]}'
                                )
                            shutil.copy(
                                archivo,
                                f'{ARMONY_DOCS}/{aux_path}/{archivo.split("/")[-1]}')
                        # Hacemos Submit para su aprobación
                        id = data['_id']
                        a_id = data['_activity_instance_id'][0]
                        url = f"https://recsa.kissflow.com/process/2/{account_id}/Documentos_convenios_Armony_PE/{id}/{a_id}/submit"
                        headers = {"Accept": "*/*", "X-Api-Key": f"{key_api}"}
                        response = requests.request("POST", url, headers=headers)

                        #Cambiamos estado en Base de Datos
                        if estado_base == 'Envio Convenio':
                            bbdd.actualizar_estado('Revision Supervisor',
                                                'Envio Convenio',
                                                dni=data['Numero_DNI_1'])
                except Exception as e:
                    logger.error(f"{str(e)}")
                    continue
        else:
            """ No esta en la base de datos -> Rechazamos formulario"""
            id = data['_id']
            a_id = data['_activity_instance_id'][0]
            url = f"https://recsa.kissflow.com/process/2/{account_id}/Documentos_convenios_Armony_PE/{id}/{a_id}/reject"
            print(url)
            payload = {
                "Note": "Rechazado - Dato a enviar no existe en la BBDD"
            }
            headers = {
                "Accept": "*/*",
                "X-Api-Key": f"{key_api}",
                "Content-Type": "application/json"
            }
            response = requests.request("POST",
                                        url,
                                        json=payload,
                                        headers=headers)
            logger.info(f"Dato a enviar no existe en la BBDD")

            #### Para enviar datos de forma manual ####
            dni, ced, mail_ejecutivo = data[
                'Numero_DNI_1'], 'Sin_Registro', 'mauricio.pinto@armony.pe'
            aux_path = f'{dni}_{ced}'
            if not isdir(f'{DOCS}/{aux_path}'):
                logger.info('Directorio no existe en carpeta')
                os.makedirs(f'{DOCS}/{aux_path}')
                logger.info('Directorio creado')
            if not isdir(f'{ARMONY_DOCS}/{aux_path}'):
                logger.info('Directorio no existe en data clientes')
                os.makedirs(f'{ARMONY_DOCS}/{aux_path}')
                logger.info('Directorio creado')
            #Descargamos imagenes de Kissflow
            archivos = ['DNI_frontal', 'DNI_posterior', 'Convenio_Firmado']
            adjuntos = []
            for a in archivos:
                dni_frontal = data[f'{a}']
                for i in range(len(dni_frontal)):
                    direccion = dni_frontal[i]['key']
                    url_aux = f"https://recsa.kissflow.com/upload/2/{account_id}/{direccion}"
                    nombre_archivo = url_aux.split('/')[-1]
                    extension = nombre_archivo.split(".")[-1]
                    headers_aux = {
                        "Accept": "*/*",
                        "X-Api-Key": f"{key_api}",
                    }
                    response_aux = requests.get(url_aux,
                                                headers=headers_aux,
                                                stream=True)
                    if i == 0:
                        with open(f"{DOCS}/{aux_path}/{a}.{extension}",
                                  'wb') as output_file:
                            output_file.write(response_aux.content)
                        adjuntos.append(f"{DOCS}/{aux_path}/{a}.{extension}")
                    else:
                        with open(f"{DOCS}/{aux_path}/{a}_{i}.{extension}",
                                  'wb') as output_file:
                            output_file.write(response_aux.content)
                        adjuntos.append(
                            f"{DOCS}/{aux_path}/{a}_{i}.{extension}")
            for archivo in adjuntos:
                if os.path.exists(
                        f'{ARMONY_DOCS}/{aux_path}/{archivo.split("/")[-1]}'):
                    os.remove(
                        f'{ARMONY_DOCS}/{aux_path}/{archivo.split("/")[-1]}')
                logger.info(f'Copiando archivo {archivo}')
                shutil.copy(
                    archivo,
                    f'{ARMONY_DOCS}/{aux_path}/{archivo.split("/")[-1]}')

            #### Creamos archivo ZIP ####
            # if os.path.exists(f'{ARMONY_DOCS}/{aux_path}/{aux_path}.zip'):
            #     logger.info('Zip ya existe')
            #     os.remove(f'{ARMONY_DOCS}/{aux_path}/{aux_path}.zip')
            #     logger.info('Zip borrado')

            # with ZipFile(f'{ARMONY_DOCS}/{aux_path}/{aux_path}.zip', 'w', compression=ZIP_STORED) as zipObj:
            #     for archivo in adjuntos:
            #         logger.info(f'Agregando archivo {archivo} a Zip')
            #         zipObj.write(archivo, arcname=archivo.split('/')[-1], compress_type=ZIP_STORED)

            # logger.info('ZIP creado')
            link_sharepoint = f'https://recsa.sharepoint.com/sites/CentrodeExcelenciaRPA/Documentos%20compartidos/Forms/AllItems.aspx?id=%2Fsites%2FCentrodeExcelenciaRPA%2FDocumentos%20compartidos%2FData%20Clientes%2FPeru%2FArmony%20PE%2FConvenios-CartaNoAdeudo%2FDOCS%2F{aux_path}'

            send_email(
                "adrian.lino@recsa.com",
                f'Documentos Subidos por cliente {dni}',
                f'''El Cliente de DNI {dni} ha subido sus documentos.<br>
                        El convenio NO fue generado previamente por el bot, por lo que la carta de no adeudo o la solicitud de seguro deberá ser generada de forma manual.<br>
                        Puedes revisar los archivos subidos en el siguiente {fun(link_sharepoint, "<b> link </b>")}, o directamente en el formulario rechazado de Kissflow (buscar por DNI).''',
                )
           
            logger.info('Mail enviado')

            #bbdd.actualizar_estado('Revision Ejecutivo', 'Envio Convenio', dni=data['Numero_DNI_1'])



# If there are no submitions in the fase 'Validacion Documentos'
if len(datos_validar) > 0:
    try:
        for data in datos_validar:  #Pensar si hay más de dos convenios para un mismo convenio
            dict_aux = bbdd.encontrar_convenio(data['Numero_DNI_1'],
                                               'Revision Supervisor')
            #Si es que existe en la base de datos
            if len(dict_aux) > 0:
                dict_aux = dict_aux[0]
                dni, ced, mail_cliente, mail_ejecutivo = dict_aux[
                    'DNI'], dict_aux['Cedente'], dict_aux[
                        'Mail Cliente'], dict_aux['Mail Ejecutivo']
                # mail_cliente = 'mauricio.pinto@armony.pe'
                #Si los documentos son Validos
                # If documents are valid, it generates the letter of no debt
                if data['Documentos_Validos_1'] == True:
                    #Generación Carta de No Adeudo
                    rut_api = data["Numero_DNI_1"]
                    while rut_api[0] == '0':
                        rut_api = rut_api[1:]
                    cedente, destinatario, destinario2, destinario3, ruc, productos, creditos = bbdd.retornar_dato(
                        f'{rut_api}', f'{dict_aux["Cedente"]}')
                    doc = Document(f'{ROOT}/CNA_formato_v2.docx')
                    docx_value(doc, re.compile('{Nombre}'),
                               dict_aux['Nombre Cliente'])
                    docx_value(doc, re.compile('{DNI}'), dict_aux['DNI'])
                    docx_value(doc, re.compile('{Cedente2}'), cedente)
                    docx_value(doc, re.compile('{Destinatario}'), destinatario)
                    docx_value(doc, re.compile('{Ruc}'), ruc)
                    docx_value(doc, re.compile('{Producto_1}'), productos)
                    docx_value(doc, re.compile('{Crédito_1}'), creditos)
                    docx_path = f'{ROOT}/CNA/DOCX/CNA_{dict_aux["DNI"]}_{dict_aux["Cedente"]}.docx'
                    pdf_path = f'{ROOT}/CNA/PDF/CNA_{dict_aux["DNI"]}_{dict_aux["Cedente"]}.pdf'
                    doc.save(docx_path)
                    convert(docx_path, pdf_path)
                    docs_cna = f'{DOCS}/{dict_aux["DNI"]}_{dict_aux["Cedente"]}/CNA_{dict_aux["DNI"]}_{dict_aux["Cedente"]}.pdf'
                    armony_cna = f'{ARMONY_DOCS}/{dict_aux["DNI"]}_{dict_aux["Cedente"]}/CNA_{dict_aux["DNI"]}_{dict_aux["Cedente"]}.pdf'
                    shutil.copy(pdf_path, docs_cna)
                    shutil.copy(pdf_path, armony_cna)
                    #Se envia el correo
                    # COMPLETADO
                    # REVIEW: COLOCAR UN IF -> SI SOLICITO CARTA DE NO ADEUDO ENVIAR MAIL DE ACEPTACION
                    # COMPLETADO
                    if (data["Quieres_obtener_tu_carta_de_no_adeudo"] == True or
                        data["Quieres_obtener_tu_carta_de_no_adeudo"] == None):
                        send_email(
                            "adrian.lino@recsa.com",
                            'Felicitaciones! Haz conseguido tu Carta de No Adeudo',
                            'Haz completado todos los pasos del proceso para obtener tu Carta de No-Adeudo. <br> Te adjuntamos el archivo en este correo.',
                            attachment_location=pdf_path,
                            )
                        
                        logger.info(f"Correo 'Carta no adeudo' enviado ")


                    # ---------------------------------------------------------------------------- #
                    # -------------------- ERROR: SUBMITION ENDS UP WITH ERROR ------------------- #
                    # ---------------------------------------------------------------------------- #
                    id = data['_id']
                    a_id = data['_activity_instance_id'][0]
                    url = f"https://recsa.kissflow.com/process/2/{account_id}/Documentos_convenios_Armony_PE/{id}/{a_id}/submit"
                    headers = {"Accept": "*/*", "X-Api-Key": f"{key_api}"}
                    response = requests.request("POST", url, headers=headers)
                    logger.info(f'Formulario aprobado en kissflow')
                    # ---------------------------------------------------------------------------- #
                    # -------------------- ERROR: SUBMITION ENDS UP WITH ERROR ------------------- #
                    # ---------------------------------------------------------------------------- #

                    # ---------------------------------------------------------------------------- #
                    # ----------------------- RESPONSE MESSAGE FROM SERVER ----------------------- #
                    # ---------------------------------------------------------------------------- #

                    # {"_id":"3cd7f81a-d95f-497a-95da-1b5d26bdb283",
                    # "type":"processError",
                    # "error_code":"process",
                    # "status":"error",
                    # "en_message":"An unexpected error has occurred. Please contact our support team.",
                    # "message":"An unexpected error has occurred. Please contact our support team.",
                    # "request_id":"process.submit-item-10388d9c-af1a-4945-9da0-c96308259d5e"}

                    # ---------------------------------------------------------------------------- #
                    # ----------------------- RESPONSE MESSAGE FROM SERVER ----------------------- #
                    # ---------------------------------------------------------------------------- #
                    #Se actualiza base de datos
                    bbdd.actualizar_estado('Carta Generada',
                                           'Revision Supervisor',
                                           dni=data['Numero_DNI_1'])
                    logger.info(f'Se actuliza BBDD a Carta Generada')
                    # TODO: Enviar datos de seguro al servidor
                    try:
                        bbdd.actualizar_estado2(data['Numero_DNI_1'])
                    except Exception as e:
                        logger.error(e)

                #Se rechaza solicitud y se actualiza base de datos
                else:
                    id = data['_id']
                    a_id = data['_activity_instance_id'][0]
                    url = f"https://recsa.kissflow.com/process/2/{account_id}/Documentos_convenios_Armony_PE/{id}/{a_id}/reject"
                    print(url)
                    payload = {"Note": "Rechazado "}
                    headers = {
                        "Accept": "*/*",
                        "X-Api-Key": f"{key_api}",
                        "Content-Type": "application/json"
                    }
                    response = requests.request("POST",
                                                url,
                                                json=payload,
                                                headers=headers)
                    logger.info(f'Formulario rechazado en kissflow')

                    #Se actualiza base de datos
                    bbdd.actualizar_estado('Envio Convenio',
                                           'Revision Supervisor',
                                           dni=data['Numero_DNI_1'])
                    logger.info(f'Se actualiza BBDD a Envio Convenio')

                    #Se envia mail al cliente explicando por que no fue aprobado
                    # * COMPLETADO
                    # TODO: COLOCAR UN IF -> SI SOLICITO CARTA DE NO ADEUDO ENVIAR MAIL DE RECHAZO
                    # * COMPLETADO
                    if (data["Quieres_obtener_tu_carta_de_no_adeudo"] == True or
                        data["Quieres_obtener_tu_carta_de_no_adeudo"] == None):
                        send_email(
                            "adrian.lino@recsa.com",
                            'Rechazo de Solicitud de Carta de No Adeudo',
                            f'{data["Mensaje_Rechazo"]} <br> Puede subir nuevamente sus documentos en el {fun("https://recsa.kissflow.com/public/Pf10cbc784-4f38-4b64-b657-4d5643c36b16", "SIGUIENTE LINK")}',
                            )
                        
                        logger.info(f"Correo enviado 'Rechazo carta no adeudo'")


            else:
                # ---------------------------------------------------------------------------- #
                # -------------------- ERROR: SUBMITION ENDS UP WITH ERROR ------------------- #
                # ---------------------------------------------------------------------------- #
                id = data['_id']
                a_id = data['_activity_instance_id'][0]
                url = f"https://recsa.kissflow.com/process/2/{account_id}/Documentos_convenios_Armony_PE/{id}/{a_id}/submit"
                logger.info(url)
                headers = {"Accept": "*/*", "X-Api-Key": f"{key_api}"}
                response = requests.request("POST", url, headers=headers)
                logger.info(response.text)
                logger.info(f'Formulario aprobado en kissflow')

                # ---------------------------------------------------------------------------- #
                # -------------------- ERROR: SUBMITION ENDS UP WITH ERROR ------------------- #
                # ---------------------------------------------------------------------------- #

                # ---------------------------------------------------------------------------- #
                # ----------------------- RESPONSE MESSAGE FROM SERVER ----------------------- #
                # ---------------------------------------------------------------------------- #

                # {"_id":"3cd7f81a-d95f-497a-95da-1b5d26bdb283",
                # "type":"processError",
                # "error_code":"process",
                # "status":"error",
                # "en_message":"An unexpected error has occurred. Please contact our support team.",
                # "message":"An unexpected error has occurred. Please contact our support team.",
                # "request_id":"process.submit-item-10388d9c-af1a-4945-9da0-c96308259d5e"}

                # ---------------------------------------------------------------------------- #
                # ----------------------- RESPONSE MESSAGE FROM SERVER ----------------------- #
                # ---------------------------------------------------------------------------- #



    except Exception as e:
        logger.error(e)


logger.info(f"Termino ejecucion documentos.py")
logger.info("-" * 80)
logger.removeHandler(fh)
fh.close()