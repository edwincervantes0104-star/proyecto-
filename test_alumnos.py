import unittest
from unittest.mock import patch, MagicMock
from app import app, mysql


class TestAlumnos(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.mysql")
    @patch("app.fetchall")
    def test_listar_alumnos(self, mock_fetchall, mock_mysql):
        """Prueba GET /alumno para ver si carga la página."""
        mock_fetchall.return_value = []

        response = self.client.get("/alumno")

        self.assertEqual(response.status_code, 200)

    @patch("app.mysql")
    def test_registrar_alumno(self, mock_mysql):
        """Prueba registrar alumno."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post("/alumno", data={
            "no_control": "20250001",
            "curp": "TEST010101HDFABC01",
            "nombre": "Juan",
            "apellido_paterno": "Pérez",
            "apellido_materno": "Gómez",
            "turno": "Matutino",
            "grupo": "3A",
            "semestre": "3"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alumno registrado", response.data)

    @patch("app.mysql")
    @patch("app.fetchone")
    @patch("app.fetchall")
    def test_editar_alumno(self, mock_fetchall, mock_fetchone, mock_mysql):
        """Prueba actualizar alumno."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        # Simular alumno existente
        mock_fetchone.return_value = {
            "id": 10,
            "no_control": "20250001",
            "curp": "TEST010101HDFABC01",
            "nombre": "Juan",
            "apellido_paterno": "Pérez",
            "apellido_materno": "Gómez",
            "turno": "Matutino",
            "grupo": "3A",
            "semestre": "3"
        }

        mock_fetchall.return_value = []

        response = self.client.post("/alumno/editar/10", data={
            "no_control": "20250002",
            "curp": "CURP010101ABCDEF01",
            "nombre": "Luis",
            "apellido_paterno": "Martínez",
            "apellido_materno": "Soto",
            "turno": "Vespertino",
            "grupo": "4B",
            "semestre": "4"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alumno actualizado", response.data)

    @patch("app.mysql")
    def test_eliminar_alumno(self, mock_mysql):
        """Prueba eliminar alumno."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get("/alumno/eliminar/20", follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alumno eliminado", response.data)


if __name__ == "_main_":
    unittest.main()