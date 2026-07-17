import unittest

import pandas as pd

from asesorias_app.services.registro_service import RegistroService


class MemoryRepository:
    def __init__(self, df):
        self.df = df.copy()

    def load_registro(self):
        return self.df.copy()

    def save_registro(self, df):
        self.df = df.copy()


def base_df():
    return pd.DataFrame(
        [
            {
                "Cédula": "A",
                "Nombre_Usuario": "Ana",
                "Correo_Electronico": "ana@u.edu",
                "Título_Trabajo_Grado": "Tesis X",
                "Asesor metodológico": "Asesor 1",
                "Nombre_Facultad": "Facultad 1",
            },
            {
                "Cédula": "B",
                "Nombre_Usuario": "Bea",
                "Correo_Electronico": "bea@u.edu",
                "Título_Trabajo_Grado": "Tesis X",
                "Asesor metodológico": "Asesor 1",
                "Nombre_Facultad": "Facultad 1",
            },
            {
                "Cédula": "C",
                "Nombre_Usuario": "Caro",
                "Correo_Electronico": "caro@u.edu",
                "Título_Trabajo_Grado": "Tesis X",
                "Asesor metodológico": "Asesor 1",
                "Nombre_Facultad": "Facultad 1",
            },
            {
                "Cédula": "D",
                "Nombre_Usuario": "Diana",
                "Correo_Electronico": "diana@u.edu",
                "Título_Trabajo_Grado": "Tesis Z",
                "Asesor metodológico": "Asesor Z",
                "Nombre_Facultad": "Facultad Z",
            },
        ]
    )


class RegistroEditModesTest(unittest.TestCase):
    def test_individual_update_changes_only_target_row(self):
        repo = MemoryRepository(base_df())
        service = RegistroService(repository=repo)

        service.update_individual_by_index(
            2,
            {
                "Título_Trabajo_Grado": "Tesis Y",
                "Asesor metodológico": "Asesor 2",
                "Correo_Electronico": "caro.nuevo@u.edu",
            },
        )

        df = repo.load_registro()
        self.assertEqual(df.loc[2, "Título_Trabajo_Grado"], "Tesis Y")
        self.assertEqual(df.loc[2, "Asesor metodológico"], "Asesor 2")
        self.assertEqual(df.loc[2, "Correo_Electronico"], "caro.nuevo@u.edu")
        self.assertEqual(df.loc[0, "Título_Trabajo_Grado"], "Tesis X")
        self.assertEqual(df.loc[1, "Título_Trabajo_Grado"], "Tesis X")
        self.assertEqual(df.loc[0, "Asesor metodológico"], "Asesor 1")
        self.assertEqual(df.loc[1, "Asesor metodológico"], "Asesor 1")

    def test_thesis_group_update_keeps_personal_fields(self):
        repo = MemoryRepository(base_df())
        service = RegistroService(repository=repo)

        updated = service.update_thesis_group_by_indices(
            [0, 1, 2],
            {
                "Título_Trabajo_Grado": "Tesis Y",
                "Asesor metodológico": "Asesor 2",
                "Cédula": "COPIADA",
                "Nombre_Usuario": "Nombre copiado",
                "Correo_Electronico": "copiado@u.edu",
            },
        )

        df = repo.load_registro()
        self.assertEqual(updated, 3)
        self.assertEqual(df.loc[0, "Título_Trabajo_Grado"], "Tesis Y")
        self.assertEqual(df.loc[1, "Título_Trabajo_Grado"], "Tesis Y")
        self.assertEqual(df.loc[2, "Título_Trabajo_Grado"], "Tesis Y")
        self.assertEqual(df.loc[0, "Asesor metodológico"], "Asesor 2")
        self.assertEqual(df.loc[1, "Asesor metodológico"], "Asesor 2")
        self.assertEqual(df.loc[2, "Asesor metodológico"], "Asesor 2")
        self.assertEqual(df.loc[0, "Cédula"], "A")
        self.assertEqual(df.loc[1, "Nombre_Usuario"], "Bea")
        self.assertEqual(df.loc[2, "Correo_Electronico"], "caro@u.edu")
        self.assertEqual(df.loc[3, "Título_Trabajo_Grado"], "Tesis Z")

    def test_empty_group_indices_do_not_update(self):
        repo = MemoryRepository(base_df())
        service = RegistroService(repository=repo)

        with self.assertRaises(ValueError):
            service.update_thesis_group_by_indices([], {"Título_Trabajo_Grado": "Tesis Y"})

        self.assertEqual(repo.load_registro().loc[0, "Título_Trabajo_Grado"], "Tesis X")

if __name__ == "__main__":
    unittest.main()
