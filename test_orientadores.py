import unittest
from unittest.mock import patch, MagicMock
from app import app, mysql

class TestOrientadores(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("app.mysql")
    def test_registrar_orientador(self, mock_mysql):
        """Prueba registrar orientador usando mocks."""

        # Simular cursor
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post("/orientador", data={
            "numero_empleado": "1001",
            "nombre": "Juan Perez",
            "grupos_atendidos": "1A,2B"
        }, follow_redirects=True)

        # Verifica que ejecutó el INSERT
        mock_cursor.execute.assert_called()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Orientador registrado", response.data)

    @patch("app.mysql")
    def test_editar_orientador(self, mock_mysql):
        """Prueba editar orientador."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        # Simular que SELECT regrese un orientador
        mock_cursor.fetchone.return_value = {
            "numero_empleado": 2001,
            "nombre": "Original",
            "grupos_atendidos": "3A"
        }
        mock_cursor.fetchall.return_value = []

        response = self.client.post("/orientador/editar/2001", data={
            "nombre": "Nuevo",
            "grupos_atendidos": "5B"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Orientador actualizado", response.data)

    @patch("app.mysql")
    def test_eliminar_orientador(self, mock_mysql):
        """Prueba eliminar orientador."""

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get("/orientador/eliminar/3001", follow_redirects=True)

        mock_cursor.execute.assert_called()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Orientador eliminado", response.data)


if __name__ == "__main__":
    unittest.main()