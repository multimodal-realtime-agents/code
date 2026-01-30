Follow these steps to run the application locally:

1. **Install Dependencies:**

   Install dependencies that include [Agent Development Kit](https://google.github.io/adk-docs/):
   ```bash
   pip install -r ../../requirements.txt
   ```

2. **Configure Environment Variables:**

   Navigate to the backend directory:
   ```bash
   cd backend
   ```
   Copy the example environment file:
   ```bash
   cp dotenv.example .env
   ```

   Edit .env with your actual API keys and configuration:

   ```bash
   nano .env  # or use your preferred text editor
   ```

   The `dotenv.example` file contains required and optional environment variables. At a minimum, set the following:

   - `GOOGLE_GENAI_USE_VERTEXAI`: Set to 1 to use Vertex AI, 0 to use Dev endpoint
   - `GOOGLE_API_KEY`: Your Google API key (required if using Dev endpoint)
   - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID (required if using Vertex endpoint)
   - `GOOGLE_CLOUD_LOCATION`: Your Google Cloud region (required if using Vertex endpoint)

3. **Start the Backend:**

   Make sure you're in the *backend* directory 


   Start the backend:
   ```bash
   python backend.py
   ```

   The backend server will start on `localhost:8081`.

4. **Start the Frontend:**

   
   Open a new terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
   
   Start a simple HTTP server:
   ```bash
   python -m http.server 8000
   ```

5. **Access the Application:**

   Open your web browser and navigate to: `http://localhost:8000`