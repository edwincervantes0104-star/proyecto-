import unittest
from unittest.mock import patch, MagicMock
from app import app, mysql

class TestDirectivos(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.mysql")
    def test_registrar_directivo(self, mock_mysql):
        """Prueba registrar directivo."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post("/directivo", data={
            "numero_empleado": "5001",
            "nombre": "María López",
            "puesto": "Coordinadora"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Directivo registrado", response.data)

    @patch("app.mysql")
    @patch("app.fetchall")
    def test_listar_directivos(self, mock_fetchall, mock_mysql):
        """Prueba que la ruta GET regrese la página de directivos."""

        mock_fetchall.return_value = []

        response = self.client.get("/directivo")

        self.assertEqual(response.status_code, 200)

    @patch("app.mysql")
    def test_editar_directivo(self, mock_mysql):
        """Prueba editar directivo."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

       
        mock_cursor.fetchone.return_value = {
            "numero_empleado": 6001,
            "nombre": "Nombre Original",
            "puesto": "Subdirector"
        }
        mock_cursor.fetchall.return_value = []

        response = self.client.post("/directivo/editar/6001", data={
            "nombre": "Nombre Nuevo",
            "puesto": "Director General"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Directivo actualizado correctamente", response.data)

    @patch("app.mysql")
    def test_eliminar_directivo(self, mock_mysql):
        """Prueba eliminar directivo."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get("/directivo/eliminar/7001", follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Directivo eliminado", response.data)


if __name__ == "__main__":
    unittest.main()