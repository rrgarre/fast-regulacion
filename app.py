from flask import Flask, Response, send_file
import requests
from bs4 import BeautifulSoup
import csv
import io
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# credenciales
USERMCT = os.getenv("USERMCT")
PASSWORD = os.getenv("PASSWORD")

# telegram
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# endpoints
LOGIN_URL = os.getenv("LOGIN_URL")
DATOS_URL = os.getenv("DATOS_URL")
DETALLES_AL016 = os.getenv("DETALLES_AL016")
DETALLES_DP003 = os.getenv("DETALLES_DP003")
DETALLES_DP004 = os.getenv("DETALLES_DP004")
DETALLES_DP007 = os.getenv("DETALLES_DP007")
DETALLES_DP008 = os.getenv("DETALLES_DP008")
DETALLES_DP017 = os.getenv("DETALLES_DP017")


@app.route("/generar_csv")
def generar_csv():
  session = requests.Session()

  # --- Paso 1: GET login ----------------------------------------------------------
  resp = session.get(LOGIN_URL)
  soup = BeautifulSoup(resp.text, "html.parser")
  execution = soup.find("input", {"name": "execution"})["value"]

  # --- Paso 2: POST login ----------------------------------------------------------
  payload = {
      "username": USERMCT,
      "password": PASSWORD,
      "execution": execution,
      "_eventId": "submit",
      "geolocation": ""
  }
  resp = session.post(LOGIN_URL, data=payload, allow_redirects=True)
  if "telemetria2.mct.es" not in resp.url:
      print("⚠️ Login no parece haber funcionado. URL actual:", resp.url)

  # --- Paso 3: GET datos principales ----------------------------------------------------------
  r = session.get(DATOS_URL)
  if r.headers.get("Content-Type", "").startswith("application/json"):
      data = r.json()
  else:
      print("⚠️ No recibí JSON de datos principales.")
      return "Error: no se recibió JSON", 500

  # --- Paso 4: GET detalles AL016 ----------------------------------------------------------
  r_detalles_al016 = session.post(DETALLES_AL016, data={})
  if r_detalles_al016.headers.get("Content-Type", "").startswith("application/json"):
      detalles_al016 = r_detalles_al016.json()
  else:
      print("⚠️ No recibí JSON de detalles AL016.")
      return "Error: no se recibió JSON", 500
  # Obtener totalizador caudalímetro
  totalizador_valor = ""
  for senal in detalles_al016.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Totalizador caudalímetro":
          totalizador_valor = senal.get("valorFormateado", "")
          break
  # Obtener totalizador caudalímetro
  consigna_caudal = ""
  for senal in detalles_al016.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Consigna caudal":
          consigna_caudal = str(int(senal.get("valor", ""))) + " l/s"
          break
  # --- Paso 5: GET detalles DP003 ----------------------------------------------------------
  r_detalles_dp003 = session.post(DETALLES_DP003, data={})
  if r_detalles_dp003.headers.get("Content-Type", "").startswith("application/json"):
      detalles_dp003 = r_detalles_dp003.json()
  else:
      print("⚠️ No recibí JSON de detalles DP003.")
      return "Error: no se recibió JSON", 500
  # Sumar los 4 niveles de cámara
  niveles = ["Nivel cámara 1", "Nivel cámara 2", "Nivel cámara 3", "Nivel cámara 4"]
  suma_niveles = 0.0
  for senal in detalles_dp003.get("senalesInstalacion", []):
      if senal.get("descripcion") in niveles:
          suma_niveles += float(senal.get("valor", 0))
  suma_niveles = round(suma_niveles, 2)
  # Datos del canal viejo
  canalViejo = 0
  for senal in detalles_dp003.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Caudal canal viejo":
          canalViejo = float(senal.get("valor", 0))
  # --- Paso 6: GET detalles DP004 ----------------------------------------------------------
  r_detalles_dp004 = session.post(DETALLES_DP004, data={})
  if r_detalles_dp004.headers.get("Content-Type", "").startswith("application/json"):
      detalles_dp004 = r_detalles_dp004.json()
  else:
      print("⚠️ No recibí JSON de detalles DP004.")
      return "Error: no se recibió JSON", 500
  # Altura
  dp004Altura1 = 0.0
  dp004Altura2 = 0.0
  for senal in detalles_dp004.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Nivel cámara 1":
          dp004Altura1 = float(senal.get("valor", 0))
          break
  for senal in detalles_dp004.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Nivel cámara 2":
          dp004Altura2 = float(senal.get("valor", 0))
          break
  dp004Altura = max(dp004Altura1, dp004Altura2)
  # Caudal de entrada
  dp004Caudal1 = 0.0
  dp004Caudal2 = 0.0
  for senal in detalles_dp004.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Caudal entrada 1":
          dp004Caudal1 = float(senal.get("valor", 0))
          break
  for senal in detalles_dp004.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Caudal entrada 2":
          dp004Caudal2 = float(senal.get("valor", 0))
          break
  dp004Caudal = round((dp004Caudal1 + dp004Caudal2)/10)*10
  # --- Paso 7: GET detalles DP007 ----------------------------------------------------------
  r_detalles_dp007 = session.post(DETALLES_DP007, data={})
  if r_detalles_dp007.headers.get("Content-Type", "").startswith("application/json"):
      detalles_dp007 = r_detalles_dp007.json()
  else:
      print("⚠️ No recibí JSON de detalles DP007.")
      return "Error: no se recibió JSON", 500
  # Aportacion NCC
  dp007Aportacion = 0.0
  for senal in detalles_dp007.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Caudal a nuevo canal de Cartagena":
          dp007Aportacion = round(float(senal.get("valor", 0)) * 3.4 / 100) * 100
          break
  # --- Paso 8: GET detalles DP008 ----------------------------------------------------------
  r_detalles_dp008 = session.post(DETALLES_DP008, data={})
  if r_detalles_dp008.headers.get("Content-Type", "").startswith("application/json"):
      detalles_dp008 = r_detalles_dp008.json()
  else:
      print("⚠️ No recibí JSON de detalles DP008.")
      return "Error: no se recibió JSON", 500
  # Altura
  dp008Altura1 = 0.0
  dp008Altura2 = 0.0
  for senal in detalles_dp008.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Nivel cámara 1":
          dp008Altura1 = float(senal.get("valor", 0))
          break
  for senal in detalles_dp008.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Nivel cámara 2":
          dp008Altura2 = float(senal.get("valor", 0))
          break
  dp008Altura = max(dp008Altura1, dp008Altura2)
  # Aportacion NCC
  dp008Aportacion = 0.0
  for senal in detalles_dp008.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Caudal a nuevo canal de Cartagena":
          dp008Aportacion = round(float(senal.get("valor", 0)) * 3.4 / 100) * 100
          break
  # --- Paso 9: GET detalles DP017 ----------------------------------------------------------
  r_detalles_dp017 = session.post(DETALLES_DP017, data={})
  if r_detalles_dp017.headers.get("Content-Type", "").startswith("application/json"):
      detalles_dp017 = r_detalles_dp017.json()
  else:
      print("⚠️ No recibí JSON de detalles DP017.")
      return "Error: no se recibió JSON", 500
  # Vistabella
  dp017Caudal = 0.0
  for senal in detalles_dp017.get("senalesInstalacion", []):
      if senal.get("descripcion") == "Caudal a depósito de Vistabella (DP043)":
          dp017Caudal = round(float(senal.get("valor", 0)) * 3.4 / 100) * 100
          break
  # --- Paso 10: Crear CSV ----------------------------------------------------------
  with open("datos.csv", "w", newline="", encoding="utf-8") as f:
      writer = csv.writer(f)
      writer.writerow(["descripcion", "valor_NIVEL_01"])
      valores_dict = {}
      # Datos principales
      for obj in data:
          descripcion = obj.get("descripcion", "")
          valor = ""
          for senal in obj.get("senalesPrincipales", []):
              if senal.get("codigo") == "NIVEL_01":
                  valor = senal.get("valor", "")
                  valores_dict[descripcion] = valor
                  break
          writer.writerow([descripcion, valor])
      # Fila AL016
      writer.writerow(["totalizador pozo los palos", totalizador_valor])
      # Fila DP003
      writer.writerow(["Tentegorra", suma_niveles])
      # Fila DP003 caudal canal viejo
      writer.writerow(["canal viejo", round(canalViejo)])
      # Fila DP004 altura
      writer.writerow(["altura Mirador", dp004Altura])
      # Fila DP004 caudal entrada
      writer.writerow(["caudal entrada Mirador", dp004Caudal])
      # Fila DP007 caudal aportacion NCC
      writer.writerow(["aportacion Romero1", dp007Aportacion])
      # Fila DP008 altura
      writer.writerow(["altura Romero2", dp008Altura])
      # Fila DP008 caudal aportacion NCC
      writer.writerow(["aportacion Romero2", dp008Aportacion])
      # Fila DP017 caudal Vistabella
      writer.writerow(["Vistabella", dp017Caudal])
  print("✅ CSV generado: datos.csv")

  # --- Paso 11: Crear CSV especial con formato específico -------------------------------
  with open("datos_formato_excel.csv", "w", newline="", encoding="utf-8") as f2:
      writer2 = csv.writer(f2)
      # Primera fila (combinando literales y datos)
      fila1 = [
          str(valores_dict.get("ALMENARA DE POZO LOS PALOS", "0")).replace(".", ","),
          consigna_caudal,
          str(valores_dict.get("PARTIDOR DE SIFÓN DE LA GUÍA", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LA ALJORRA", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LA NACIONAL", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE EL JIMENADO", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LOS MUÑOCES", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LA MARAÑA", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LOS GITANOS", "0")).replace(".", ","),
          "",
          str(dp004Altura).replace(".", ","),
          dp004Caudal,
          str(valores_dict.get("PARTIDOR DE EL MIRADOR", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE EL MIRADOR", "0")).replace(".", ","),
          "",
          "",
          dp007Aportacion,
          str(dp008Altura).replace(".", ","),
          dp008Aportacion,
          str(valores_dict.get("ALMENARA DE LOS LLANOS", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LAS PEÑAS", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE LAS COLINAS", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE SAN MIGUEL DE SALINAS", "0")).replace(".", ","),
          "",
          str(valores_dict.get("ALMENARA DE TORREMENDO", "0")).replace(".", ","),
          "",
          0,
          4400
      ]
      writer2.writerow(fila1)
      # Segunda fila (literales con los datos extraídos)
      fila2 = [
          "Altura de Tentegorra", str(suma_niveles).replace(".", ","),
          "Canal viejo", round(canalViejo),
          "Totalizador Pozo los Palos", totalizador_valor,
          "Vistabella", dp017Caudal
      ]
      writer2.writerow(fila2)

      print("✅ CSV con formato específico generado: datos_formato_excel.csv")

  # ---- Archivo en variable para usarlo en los siguientes apartados de ENVIAR por diferentes vias
  archivo = "datos_formato_excel.csv"

  # --- Paso 12: Enviar CSV a TELEGRAM -------------------------------
  with open(archivo, "rb") as f:
      requests.post(
          f"https://api.telegram.org/bot{TOKEN}/sendDocument",
          data={"chat_id": CHAT_ID},
          files={"document": f}
      )

  # ------------ responder como descarga ----------------------------------
  # return send_file(
  #     archivo,
  #     mimetype="text/csv",
  #     as_attachment=True,
  #     download_name="datos_formato_excel.csv"
  # )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
