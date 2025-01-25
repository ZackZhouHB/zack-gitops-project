document.getElementById('imageUpload').addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const previewImage = document.getElementById('previewImage');
            previewImage.src = e.target.result;
            previewImage.style.display = 'block'; // Show the image
        };
        reader.readAsDataURL(file); // Read the file as a data URL
    }
});

document.getElementById('uploadForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const fileInput = document.getElementById('imageUpload');
    const resultDiv = document.getElementById('result');

    if (fileInput.files.length === 0) {
        resultDiv.textContent = 'Please select an image.';
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://localhost:5000/predict', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to get prediction');
        }

        const data = await response.json();
        resultDiv.textContent = `Prediction: ${data.prediction}`;
    } catch (error) {
        resultDiv.textContent = 'Error: ' + error.message;
    }
});