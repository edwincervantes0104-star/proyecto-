import unittest
from unittest.mock import patch, MagicMock
from app import app


class TestMaterias(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # ---------- Registrar Materia ----------
    @patch("app.mysql")
    @patch("app.fetchall")
    def test_registrar_materia(self, mock_fetchall, mock_mysql):

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor
        mock_fetchall.return_value = []  # evitar errores del GET final

        response = self.client.post("/materia", data={
            "estructura_curricular": "Básica",
            "nombre_materia": "Matemáticas I",
            "horas_semana": "5",
            "horas_totales": "80",
            "creditos": "6"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Materia registrada correctamente", response.data)

    # ---------- Editar Materia ----------
    @patch("app.mysql")
    @patch("app.fetchone")
    @patch("app.fetchall")
    def test_editar_materia(self, mock_fetchall, mock_fetchone, mock_mysql):

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        mock_fetchone.return_value = {
            "id": 1,
            "estructura_curricular": "Básica",
            "nombre_materia": "Materia Original",
            "horas_semana": 4,
            "horas_totales": 70,
            "creditos": 5
        }
        mock_fetchall.return_value = []

        response = self.client.post("/materia/editar/1", data={
            "estructura_curricular": "Formativa",
            "nombre_materia": "Materia Editada",
            "horas_semana": "6",
            "horas_totales": "100",
            "creditos": "8"
        }, follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Materia actualizada correctamente", response.data)

    # ---------- Eliminar Materia ----------
    @patch("app.mysql")
    @patch("app.fetchall")
    def test_eliminar_materia(self, mock_fetchall, mock_mysql):

        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor
        mock_fetchall.return_value = []

        response = self.client.get("/materia/eliminar/5", follow_redirects=True)

        mock_cursor.execute.assert_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Materia eliminada correctamente", response.data)


if __name__ == "__main__":
    unittest.main()