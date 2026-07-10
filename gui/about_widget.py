from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from version import VERSION, CREATOR


class AboutWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        heading = QLabel("About")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        lines = [
            f"AniListSync v{VERSION}",
            f"by {CREATOR}",
            "",
            "Import anime titles from Telegram Saved Messages",
            "and sync them to AniList and MyAnimeList.",
            "",
            "Built with: Python, PyQt6, Telethon, Rich",
            "License: MIT",
        ]
        for line in lines:
            lbl = QLabel(line)
            if line:
                lbl.setStyleSheet("color: #c0caf5; font-size: 13px;")
            else:
                lbl.setStyleSheet("color: #565f89;")
                lbl.setFixedHeight(8)
            layout.addWidget(lbl)

        layout.addStretch()
        self.setLayout(layout)
