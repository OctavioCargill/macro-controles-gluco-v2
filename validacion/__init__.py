"""Validación de una liquidación contra la Power App (captura de pantalla) y contra su factura (PDF).

Todo corre en la PC: el OCR (RapidOCR, con sus modelos incluidos) y la lectura de PDFs no usan internet.
- lectura.py: texto y posición de cada renglón de una imagen o de un PDF.
- comparador.py: dato por dato, si coincide, si es distinto o si no se ve.
"""
