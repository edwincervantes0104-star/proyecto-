import unittest
from unittest.mock import patch, MagicMock
from app import app, mysql

class TestProfesores(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # ------- Registrar profesor -------
    @patch("app.mysql")
    @patch("app.fetchall")
    def test_registrar_profesor(self, mock_fetchall, mock_mysql):
        """Prueba registrar profesor."""
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor
        mock_fetchall.return_value = []

        response = self.client.post("/profesor", data={
            "numero_empleado": "9001",
            "nombre_docente": "Carlos Martínez",
            "fecha_ingreso": "2022-01-10",
            "perfil_profesional": "Ingeniería",
            "asignatura": "Matemáticas"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Profesor registrado", response.data)

    # ------- Editar profesor -------
    @patch("app.mysql")
    @patch("app.fetchone")
    @patch("app.fetchall")
    def test_editar_profesor(self, mock_fetchall, mock_fetchone, mock_mysql):
        """Prueba editar profesor."""
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        # Simular datos existentes
        mock_fetchone.return_value = {
            "numero_empleado": 9002,
            "nombre_docente": "Original",
            "fecha_ingreso": "2020-01-01",
            "perfil_profesional": "Maestría",
            "asignatura": "Física"
        }
        mock_fetchall.return_value = []

        response = self.client.post("/profesor/editar/9002", data={
            "nombre_docente": "Nuevo Nombre",
            "fecha_ingreso": "2023-01-15",
            "perfil_profesional": "Doctorado",
            "asignatura": "Química"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Profesor actualizado", response.data)

    # ------- Eliminar profesor -------
    @patch("app.mysql")
    def test_eliminar_profesor(self, mock_mysql):
        """Prueba eliminar profesor."""
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get("/profesor/eliminar/9003", follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Profesor eliminado", response.data)

if __name__ == "__main__":
    unittest.main()
    #cervantes2903