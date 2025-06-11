import pygame
import sys
import os
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
from tkinter import filedialog, Tk
import shutil

# === Setup UI ===
pygame.init()
screen = pygame.display.set_mode((600, 300))
pygame.display.set_caption("Cubing Comp Tool")
font = pygame.font.SysFont("Arial", 24)
clock = pygame.time.Clock()

# === UI Helper ===
def draw_text(text, x, y):
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (x, y))

# === File Picker ===
def select_csv_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    root.destroy()
    return file_path

# === Group Generator Function ===
def assign_groups(df, group_size=2):
    output_df = df.copy()
    all_events = set()
    for events in df["Events"]:
        all_events.update(events.split(":"))

    for event in all_events:
        mask = df["Events"].apply(lambda x: event in x.split(":"))
        competitors = df[mask].sort_values("Name").reset_index()
        num_groups = math.ceil(len(competitors) / group_size)
        group_numbers = [(i % num_groups) + 1 for i in range(len(competitors))]
        for i, idx in enumerate(competitors["index"]):
            output_df.at[idx, event] = group_numbers[i]
    return output_df

# === PDF Classes ===
class MultiScorecardPDF(FPDF):
    def header(self): pass
    def create_scorecard_block(self, name, event, station, x, y):
        self.set_xy(x, y)
        self.set_font("Arial", size=8)
        self.cell(95, 65, '', border=1)
        self.set_xy(x + 2, y + 2)
        self.cell(0, 4, f"Name: {name}", ln=True)
        self.set_x(x + 2); self.cell(0, 4, f"Event: {event}", ln=True)
        self.set_x(x + 2); self.cell(0, 4, f"Round: 1", ln=True)
        self.set_x(x + 2); self.cell(0, 4, f"Station: {station}", ln=True)
        self.ln(1)
        for i in range(7):
            self.set_x(x + 2)
            self.cell(20, 6, f"{i+1}.", border=1)
            self.cell(18, 6, "", border=1)
            self.cell(20, 6, "", border=1)
            self.cell(20, 6, "", border=1)
            self.cell(15, 6, "", border=1, ln=True)

class GroupedNamecardPDF(FPDF):
    def header(self): pass
    def create_namecard(self, name, events, row_data, x, y):
        self.set_xy(x, y)
        self.set_font("Arial", size=12)
        self.cell(90, 55, '', border=1)
        self.set_xy(x + 5, y + 5)
        self.set_font("Arial", 'B', 14)
        self.cell(0, 8, name, ln=True)
        self.set_xy(x + 5, y + 20)
        self.set_font("Arial", size=9)
        event_lines = []
        for event in events.split(":"):
            station = row_data.get(event)
            event_lines.append(f"{event}: Group {int(station)}" if pd.notna(station) else f"{event}: -")
        self.multi_cell(0, 6, "\n".join(event_lines))

# === Main Logic ===
def run_tool(input_csv):
    df = pd.read_csv(input_csv)
    grouped_df = assign_groups(df)

    date_folder = datetime.now().strftime("comp_output_%Y%m%d_%H%M%S")
    os.makedirs(date_folder, exist_ok=True)
    grouped_csv_path = os.path.join(date_folder, "grouped_competitors.csv")
    grouped_df.to_csv(grouped_csv_path, index=False)

    # Scorecards
    scorecard_pdf = MultiScorecardPDF()
    scorecard_pdf.set_auto_page_break(auto=False)
    scorecard_pdf.add_page()
    row_idx = col_idx = 0
    for _, row in grouped_df.iterrows():
        for event in row["Events"].split(":"):
            if event in grouped_df.columns and pd.notna(row[event]):
                x, y = 10 + col_idx * 105, 10 + row_idx * 75
                scorecard_pdf.create_scorecard_block(row['Name'], event, int(row[event]), x, y)
                row_idx += 1
                if row_idx == 4:
                    row_idx = 0
                    col_idx += 1
                    if col_idx == 2:
                        col_idx = 0
                        scorecard_pdf.add_page()
    scorecard_pdf.output(os.path.join(date_folder, "multi_scorecards.pdf"))

    # Namecards
    namecard_pdf = GroupedNamecardPDF()
    namecard_pdf.set_auto_page_break(auto=False)
    namecard_pdf.add_page()
    row_idx = col_idx = 0
    for _, row in grouped_df.iterrows():
        x, y = 10 + col_idx * 105, 10 + row_idx * 60
        namecard_pdf.create_namecard(row['Name'], row['Events'], row.to_dict(), x, y)
        row_idx += 1
        if row_idx == 5:
            row_idx = 0
            col_idx += 1
            if col_idx == 2:
                col_idx = 0
                namecard_pdf.add_page()
    namecard_pdf.output(os.path.join(date_folder, "grouped_namecards.pdf"))
    # copy results file to folder
    shutil.copy("results.xls", os.path.join(date_folder, "results.xls"))

    return date_folder

# === Main UI Loop ===
selected_file = None
done = False
while not done:
    screen.fill((30, 30, 30))
    draw_text("Cubing Comp Tool", 20, 20)
    draw_text("1. Press [O] to open a competitor CSV", 20, 80)
    draw_text("2. Press [R] to run all steps", 20, 120)
    draw_text("3. Press [ESC] to quit", 20, 160)

    if selected_file:
        draw_text(f"Loaded: {os.path.basename(selected_file)}", 20, 200)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True
            elif event.key == pygame.K_o:
                selected_file = select_csv_file()
            elif event.key == pygame.K_r and selected_file:
                folder = run_tool(selected_file)
                draw_text(f"Saved to folder: {folder}", 20, 240)
                pygame.display.flip()
                pygame.time.wait(3000)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
