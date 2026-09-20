# -*- coding: utf-8 -*-
"""Tests mínimos del registro público de SIWA.

Validan lo esencial sin instalar nada (solo biblioteca estándar):
- que todos los datos publicados sean JSON bien formado,
- que los conjuntos con procedencia lleven su bloque de atribución,
- que las licencias del repositorio estén declaradas.

Se corren con:  python -m unittest discover -s tests
"""
import glob
import json
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLICO = os.path.join(RAIZ, "datos", "publico")


def _archivos_json():
    return glob.glob(os.path.join(PUBLICO, "*.json"))


class TestDatosPublicos(unittest.TestCase):
    def test_hay_datos_publicados(self):
        self.assertTrue(os.path.isdir(PUBLICO), "debe existir datos/publico/")
        self.assertGreater(len(_archivos_json()), 0, "debe haber datos publicados")

    def test_todo_json_es_valido(self):
        rotos = []
        for f in _archivos_json():
            try:
                with open(f, encoding="utf-8") as fh:
                    json.load(fh)
            except (ValueError, OSError) as e:
                rotos.append("%s: %s" % (os.path.basename(f), e))
        self.assertEqual(rotos, [], "hay JSON roto: %s" % rotos)

    def test_procedencia_lleva_fuente_y_calificacion(self):
        con_procedencia = 0
        con_atribucion = 0
        for f in _archivos_json():
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            if isinstance(d, dict) and "procedencia" in d:
                con_procedencia += 1
                p = d["procedencia"]
                self.assertIn(
                    "fuente", p, "%s: procedencia sin fuente" % os.path.basename(f)
                )
                self.assertIn(
                    "calificacion",
                    p,
                    "%s: procedencia sin calificacion" % os.path.basename(f),
                )
                if "atribucion" in p:
                    con_atribucion += 1
        self.assertGreater(
            con_procedencia, 0, "al menos un conjunto debe llevar procedencia"
        )
        self.assertGreater(
            con_atribucion, 0, "al menos un conjunto debe llevar atribucion"
        )

    def test_licencias_declaradas(self):
        self.assertTrue(
            os.path.exists(os.path.join(RAIZ, "LICENSE")), "falta LICENSE (código, MIT)"
        )
        self.assertTrue(
            os.path.exists(os.path.join(RAIZ, "LICENSE-DATOS.md")),
            "falta LICENSE-DATOS.md (datos, CC BY 4.0)",
        )


if __name__ == "__main__":
    unittest.main()
