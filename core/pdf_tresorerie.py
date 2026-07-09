"""Exports PDF de trésorerie."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from core.pdf_base import BasePDF
from utils.logger import get_logger

logger = get_logger(__name__)


class PdfReleverCompte(BasePDF):
    """Export PDF d'un relevé de compte."""

    def __init__(self, compte_id: int, date_debut: str = "", date_fin: str = ""):
        super().__init__("Relevé de compte", orientation="portrait", avec_page_garde=False)
        self._compte_id = compte_id
        self._date_debut = date_debut or ""
        self._date_fin = date_fin or ""

    @staticmethod
    def _montant_signe(operation: dict) -> float:
        montant = float(operation.get("montant") or 0)
        if operation.get("statut") != "valide":
            return 0.0
        type_operation = operation.get("type_operation")
        if type_operation == "recette":
            return montant
        if type_operation == "depense":
            return -montant
        if type_operation == "virement_interne":
            return montant if operation.get("source_module") == "virement_entrant" else -montant
        return 0.0

    def _construire_contenu(self) -> list:
        from db.models.tresorerie import get_compte_by_id, get_operations

        compte = get_compte_by_id(self._compte_id)
        if not compte:
            raise ValueError(f"Compte introuvable : id={self._compte_id}")

        operations = get_operations(compte_id=self._compte_id, statut="valide")
        operations = sorted(operations, key=lambda op: (str(op.get("date_operation") or ""), int(op.get("id") or 0)))

        solde_depart = float(compte.get("solde_initial") or 0)
        filtrees: list[dict] = []
        for operation in operations:
            date_operation = str(operation.get("date_operation") or "")
            if self._date_debut and date_operation < self._date_debut:
                solde_depart += self._montant_signe(operation)
                continue
            if self._date_fin and date_operation > self._date_fin:
                continue
            filtrees.append(operation)

        elements: list = [Paragraph(self.titre, self._style_titre)]
        elements.extend(self._titre_section("Informations du compte"))
        elements.append(
            self._creer_tableau(
                [
                    ["Champ", "Valeur"],
                    ["Compte", compte.get("nom") or f"Compte #{self._compte_id}"],
                    ["Type", compte.get("type_compte") or "—"],
                    ["Solde initial", self._formater_montant(compte.get("solde_initial"))],
                ],
                col_widths=[5 * cm, 11 * cm],
            )
        )
        elements.append(Spacer(1, 0.2 * cm))
        elements.extend(self._titre_section("Mouvements"))

        if not filtrees:
            elements.append(self._message_aucune_donnee())
            return elements

        donnees = [["Date", "Libellé", "Catégorie", "Type", "Montant", "Solde cumulé"]]
        total_debits = 0.0
        total_credits = 0.0
        solde_courant = solde_depart

        for operation in filtrees:
            montant_signe = self._montant_signe(operation)
            solde_courant += montant_signe
            if montant_signe >= 0:
                total_credits += montant_signe
            else:
                total_debits += abs(montant_signe)
            donnees.append(
                [
                    self._formater_date(operation.get("date_operation")),
                    operation.get("libelle") or "—",
                    operation.get("categorie_nom") or "—",
                    operation.get("type_operation") or "—",
                    self._formater_montant(montant_signe),
                    self._formater_montant(solde_courant),
                ]
            )
        donnees.append(
            [
                "Totaux",
                "",
                "",
                "",
                self._formater_montant(total_credits - total_debits),
                self._formater_montant(solde_courant),
            ]
        )
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[2.5 * cm, 4.8 * cm, 3.2 * cm, 2.5 * cm, 3 * cm, 3 * cm],
                avec_total=True,
            )
        )
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(Paragraph(f"Total débits : {self._formater_montant(total_debits)}", self._style_bold))
        elements.append(Paragraph(f"Total crédits : {self._formater_montant(total_credits)}", self._style_bold))
        elements.append(Paragraph(f"Solde final : {self._formater_montant(solde_courant)}", self._style_bold))
        return elements


class PdfSubventions(BasePDF):
    """Export PDF du récapitulatif des subventions."""

    def __init__(self, exercice: str = ""):
        super().__init__("Récapitulatif des subventions", orientation="portrait", avec_page_garde=False)
        self.exercice = exercice or self.exercice
        self._annee = self._extraire_annee(self.exercice)

    @staticmethod
    def _extraire_annee(exercice: str) -> int | None:
        chiffres = "".join(c for c in str(exercice or "") if c.isdigit())
        if len(chiffres) >= 4:
            return int(chiffres[:4])
        return None

    def _construire_contenu(self) -> list:
        from db.models.tresorerie import get_all_subventions

        elements: list = [Paragraph(self.titre, self._style_titre)]
        if self.exercice:
            elements.append(Paragraph(f"Exercice : {self.exercice}", self._style_normal))
        elements.extend(self._titre_section("Subventions"))

        subventions = get_all_subventions(annee=self._annee)
        if not subventions:
            elements.append(self._message_aucune_donnee())
            return elements

        donnees = [["Organisme", "Montant demandé", "Montant obtenu", "Statut", "Date"]]
        total_demande = 0.0
        total_obtenu = 0.0
        for subvention in subventions:
            montant_demande = float(subvention.get("montant_demande") or 0)
            montant_obtenu = float(subvention.get("montant_obtenu") or 0)
            total_demande += montant_demande
            total_obtenu += montant_obtenu
            donnees.append(
                [
                    subvention.get("organisme") or "—",
                    self._formater_montant(montant_demande),
                    self._formater_montant(montant_obtenu),
                    subvention.get("statut") or "—",
                    self._formater_date(subvention.get("date_decision") or subvention.get("date_demande")),
                ]
            )
        donnees.append(["Total", self._formater_montant(total_demande), self._formater_montant(total_obtenu), "", ""])
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[5 * cm, 3.2 * cm, 3.2 * cm, 2.8 * cm, 2.8 * cm],
                avec_total=True,
            )
        )
        return elements
