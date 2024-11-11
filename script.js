// Example: Login function to get JWT token
async function login(username, password) {
  try {
    const response = await fetch('http://127.0.0.1:8000/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }), // Send username and password for token generation
    });

    const data = await response.json();

    if (response.ok) {
      // Save token to local storage (corrected key)
      localStorage.setItem('token', data.access_token);
      alert('Login successful!');
    } else {
      // Handle error response properly
      if (data.detail) {
        alert(`Error: ${data.detail}`); // Display error details
      } else {
        alert('An unexpected error occurred.');
      }
    }
  } catch (error) {
    console.error('Error during login:', error);
    alert('Error: Something went wrong during login.');
  }
}

// Call login function with user-provided data (example usage)
login('testuser', 'testpassword');
