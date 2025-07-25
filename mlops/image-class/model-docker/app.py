from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import torch
from torchvision import transforms
from PIL import Image
import torch.nn as nn
import torchvision.models as models

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load the trained model
model = models.resnet18(pretrained=False)
model.fc = nn.Linear(model.fc.in_features, 1)
model.load_state_dict(torch.load("local_image_classifier_model.pth", map_location=torch.device('cpu')))
model.eval()

# Define the same transformations used during training
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Prediction function
def predict_image(image_path):
    image = Image.open(image_path).convert('RGB')
    image = transform(image).unsqueeze(0)
    with torch.no_grad():
        output = model(image)
        prediction = torch.sigmoid(output).item()
    return "Pneumonia (Positive)" if prediction > 0.5 else "Normal (Negative)"

# Define the endpoint
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Save the uploaded file temporarily
    file_path = "temp_image.jpeg"
    file.save(file_path)

    # Make a prediction
    result = predict_image(file_path)
    return jsonify({"prediction": result})

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)