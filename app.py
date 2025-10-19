# app.py

import pandas as pd
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
# Imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# --- Configuration ---
ATTENDANCE_LOG_FILE = 'attendance_log.csv'
STUDENTS_CSV = 'students.csv' # Ensure this file exists in the same directory

app = Flask(__name__)
# Global variable to hold student data
STUDENT_DATA = {}

# --- Helper Functions ---

def load_student_data():
    """
    Loads student data from CSV and creates the log file if it doesn't exist.
    This function has been corrected to explicitly handle columns.
    """
    global STUDENT_DATA
    try:
        # **CORRECTED LINE:** Explicitly names the three columns expected in students.csv.
        # This resolves the 'KeyError: 'Dept'' problem.
        df = pd.read_csv(STUDENTS_CSV, header=None, names=['Name', 'GRC_ID', 'Dept'])
        
        # Ensure GRC_ID is a string and used as the index
        df['GRC_ID'] = df['GRC_ID'].astype(str)
        
        # Drop duplicates based on GRC_ID, keeping the first occurrence (safety measure)
        df = df.drop_duplicates(subset=['GRC_ID'], keep='first')
        
        STUDENT_DATA = df.set_index('GRC_ID').to_dict('index')
        print("Student data loaded successfully.")
    except FileNotFoundError:
        print(f"Error: {STUDENTS_CSV} not found. Cannot load student data.")
        return
    except Exception as e:
        print(f"Error loading student data: {e}")
        return

    # Check and create the new log file with headers
    if not os.path.exists(ATTENDANCE_LOG_FILE):
        with open(ATTENDANCE_LOG_FILE, 'w') as f:
            f.write("date,grc_id,student_name,student_dept,in_time,out_time\n")
        print(f"Created attendance log file: {ATTENDANCE_LOG_FILE}")
        
    app.config['STUDENT_DATA'] = STUDENT_DATA
    
# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main QR scanning page."""
    return render_template('index.html')

# --- Updated /mark_attendance Route for In/Out Logic ---

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    """Handles check-in and check-out based on existing log state."""
    data = request.get_json()
    scanned_id = str(data.get('grc_id')).strip()
    timestamp = datetime.now()
    current_date = timestamp.strftime('%Y-%m-%d')
    current_time = timestamp.strftime('%H:%M:%S')

    # This check now relies on the corrected STUDENT_DATA dictionary having the 'Dept' key
    if scanned_id in STUDENT_DATA:
        student_info = STUDENT_DATA[scanned_id]
        student_name = student_info['Name']
        student_dept = student_info['Dept'] # This key should now exist

        try:
            # 1. READ existing log data
            try:
                df = pd.read_csv(ATTENDANCE_LOG_FILE)
            except (FileNotFoundError, pd.errors.EmptyDataError):
                df = pd.DataFrame(columns=['date', 'grc_id', 'student_name', 'student_dept', 'in_time', 'out_time'])

            # Ensure GRC_ID is string type for accurate comparison
            df['grc_id'] = df['grc_id'].astype(str)

            # 2. FIND the student's most recent *incomplete* session for today
            student_today_df = df[(df['grc_id'] == scanned_id) & (df['date'] == current_date)]
            
            # Find the latest session that hasn't been closed (out_time is NaN or empty string)
            latest_session = student_today_df[df['out_time'].fillna('').eq('')].sort_values(by='in_time', ascending=False).head(1)
            
            
            # --- 3. APPLY IN/OUT LOGIC ---
            
            if latest_session.empty:
                # SCENARIO A: CHECK-IN
                new_entry = {
                    'date': current_date,
                    'grc_id': scanned_id,
                    'student_name': student_name,
                    'student_dept': student_dept,
                    'in_time': current_time,
                    'out_time': '' # Leave out_time empty
                }
                
                df.loc[len(df)] = new_entry
                status = 'Check-In'
                message = f"Welcome, {student_name}! You are **CHECKED IN**."
                
            else:
                # SCENARIO B: CHECK-OUT
                index_to_update = latest_session.index[0]
                df.loc[index_to_update, 'out_time'] = current_time
                
                status = 'Check-Out'
                message = f"Goodbye, {student_name}! You are **CHECKED OUT**."


            # 4. WRITE the updated log data back to the CSV file
            df.to_csv(ATTENDANCE_LOG_FILE, index=False)

            return jsonify({
                'status': status,
                'message': message,
                'name': student_name,
                'grc_id': scanned_id,
                'timestamp': timestamp.strftime('%I:%M:%S %p')
            })

        except Exception as e:
            print(f"Error handling attendance: {e}")
            return jsonify({'status': 'error', 'message': f'Server error: {e}'}), 500

    else:
        # Student ID not found
        status = 'Not Found'
        message = f"Error: GRC_ID '{scanned_id}' not found in the student list."
        return jsonify({'status': status, 'message': message, 'name': 'Unknown', 'grc_id': scanned_id}), 404

# --- PDF Export Route ---

@app.route('/export_pdf')
def export_pdf():
    """Generates and serves a PDF report of the attendance log."""
    try:
        df = pd.read_csv(ATTENDANCE_LOG_FILE)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return "Attendance log not found or is empty. Nothing to export.", 404

    # Create the PDF file
    pdf_filename = 'attendance_report.pdf'
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    
    # PDF Layout Setup
    width, height = letter
    c.setFont('Helvetica-Bold', 14)
    c.drawString(1.5 * inch, height - 1 * inch, "GRC Daily Attendance Report")
    
    c.setFont('Helvetica', 10)
    
    # Headers and Positions
    headers = ["Date", "GRC ID", "Name", "In Time", "Out Time"]
    col_widths = [0.8, 1.2, 2.0, 1.0, 1.0] # Width in inches
    x_positions = [1 * inch]
    for w in col_widths[:-1]:
        x_positions.append(x_positions[-1] + w * inch)

    y_position = height - 1.5 * inch
    line_height = 0.2 * inch

    # Print Headers
    c.setFont('Helvetica-Bold', 10)
    for i, header in enumerate(headers):
        c.drawString(x_positions[i], y_position, header)
        
    y_position -= 0.1 * inch
    c.line(1 * inch, y_position, width - 1 * inch, y_position) # Divider line
    y_position -= 0.15 * inch

    # Print Data Rows
    c.setFont('Helvetica', 9)
    for index, row in df.iterrows():
        data = [
            str(row.get('date', '')),
            str(row.get('grc_id', '')),
            str(row.get('student_name', '')),
            str(row.get('in_time', '')),
            str(row.get('out_time', ''))
        ]
        
        for i, item in enumerate(data):
            c.drawString(x_positions[i], y_position, str(item))
            
        y_position -= line_height
        
        # Check for end of page
        if y_position < 0.75 * inch:
            c.showPage()
            c.setFont('Helvetica-Bold', 10)
            # Reprint headers on new page
            for i, header in enumerate(headers):
                c.drawString(x_positions[i], height - 1.5 * inch, header)
            c.line(1 * inch, height - 1.7 * inch, width - 1 * inch, height - 1.7 * inch)
            y_position = height - 2.0 * inch
            c.setFont('Helvetica', 9)
    
    c.save()
    
    # Serve the PDF
    return send_file(pdf_filename, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')


# --- Application Entry Point ---

if __name__ == '__main__':
    load_student_data() # Load data before starting server
    app.run(host='0.0.0.0', port=8000, debug=True)
