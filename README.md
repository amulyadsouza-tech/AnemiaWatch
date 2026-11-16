# AnemiaWatch 
### Machine Learning-Based, Non-Invasive Anemia Screening

AnemiaWatch is an AI-assisted healthcare screening platform that explores the use of Machine Learning and Computer Vision to estimate hemoglobin levels through smartphone-captured images of fingernail beds and lower eyelid conjunctiva.

The platform aims to make preliminary anemia screening more accessible by combining image processing, machine learning and digital health monitoring in a unified application.

---

## 🎯 Problem Statement

Traditional anemia detection primarily relies on laboratory-based blood tests, which can present accessibility, infrastructure and cost challenges, particularly in rural and underserved communities.

Limited access to diagnostic facilities can delay preliminary screening and follow-up monitoring.

**AnemiaWatch explores a technology-driven approach to address these challenges through smartphone-based image analysis and machine learning.**

---

## 💡 Proposed Solution

AnemiaWatch integrates three major components:

- **Computer Vision:** Processes smartphone images to identify relevant anatomical regions and extract visual features.
- **Machine Learning:** Analyses extracted image features to estimate hemoglobin levels, subject to model availability and validation.
- **Digital Health Platform:** Provides patient screening records, visual reports and a healthcare professional dashboard.

The platform supports two image-based screening approaches:

1. **Nail Bed Analysis** – Examines fingernail-bed images for relevant colour characteristics.
2. **Lower Eyelid Analysis** – Examines the palpebral conjunctiva for visual indicators associated with anemia.

---

## ⚙️ System Workflow

1. **Image Capture:** Capture a fingernail-bed or lower-eyelid image using a smartphone.
2. **Image Preprocessing:** Validate image quality, lighting, focus and dimensions.
3. **Region Detection:** Identify and extract the relevant anatomical Region of Interest (ROI).
4. **Feature Extraction:** Analyse relevant colour characteristics and image features.
5. **ML Inference:** Process the extracted information using the corresponding machine learning pipeline.
6. **Result Generation:** Present the estimated hemoglobin level and screening information when supported by a validated model.
7. **Health Monitoring:** Store screening records and make them accessible through the patient interface and healthcare dashboard.

---

## 🛠️ Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| UI Styling | Tailwind CSS |
| Backend | Python, FastAPI |
| Computer Vision | OpenCV |
| Machine Learning | Python, scikit-learn, PyTorch / TensorFlow (as applicable) |
| Data Processing | NumPy, Pandas |
| Database | SQLite, SQLAlchemy |
| Visualization | Recharts |

---

## ✨ Key Features

- Smartphone-based image capture and upload.
- Separate nail-bed and lower-eyelid screening workflows.
- Image preprocessing and ROI visualization.
- Machine learning-based hemoglobin estimation.
- Original and processed image comparison.
- Patient screening history.
- Visual health reports.
- Healthcare professional dashboard.
- Patient record management.

---

## 🏗️ Project Structure

```text
AnemiaWatch/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   ├── models/
│   ├── routes/
│   └── requirements.txt
│
├── Anemia_detection/
│
├── hemoglobin-deficiency-detection/
│
├── figure_detection.ipynb
│
└── README.md
```

*The structure above describes the intended organization; actual directory names may differ.*

---
Admin	admin@anemiawatch.local	admin1234
Doctor (approved)	doctor@test.com	doctor1234
Patient	test@gmail.com	test1234
## 🚀 Getting Started

### Prerequisites

- Node.js and npm
- Python 3.10+
- Git

### 1. Clone the Repository

```bash
git clone YOUR_REPOSITORY_URL
cd AnemiaWatch
```

### 2. Set Up the Backend

```bash
python -m venv venv
```

Activate the environment:

**Windows:**
```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Adjust the module path if the backend entry point differs.

### 3. Set Up the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the local URL provided by Vite in your browser.

---

## 🔬 Machine Learning Approach

The project explores image-based hemoglobin estimation through computer vision and machine learning.

The intended processing pipeline includes:

- Image acquisition and quality assessment.
- Anatomical region detection.
- ROI extraction and segmentation.
- RGB and HSV colour-space analysis.
- Feature extraction and normalization.
- Model inference and evaluation.

Model performance is assessed using appropriate regression and classification metrics, including:

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- R² Score
- Accuracy, Precision and Recall (where applicable)

Model performance and clinical applicability require independent validation using appropriately labelled datasets.

---

## 🔮 Future Scope

- Improved anatomical region detection and segmentation.
- Larger and more diverse labelled datasets.
- Model optimization for mobile devices.
- Real-time screening assistance.
- Integration with healthcare information systems.
- Multilingual accessibility.
- Clinical evaluation and validation.

---

## ⚠️ Medical Disclaimer

AnemiaWatch is an experimental, AI-assisted screening project. Its image-based predictions are not a substitute for Complete Blood Count (CBC) testing or professional medical diagnosis.

Any estimated hemoglobin values must be independently validated before clinical use. Users should consult qualified healthcare professionals for diagnosis and treatment.

---

## 👩‍💻 Project Information

**Project:** AnemiaWatch  
**Problem ID:** HF26-35  
**Domain:** Healthcare Technology | Artificial Intelligence | Machine Learning  
**Focus:** Non-Invasive Anemia Screening

---

*Making preliminary health screening more accessible through Machine Learning and Computer Vision.*
