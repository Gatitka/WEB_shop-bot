document.addEventListener('DOMContentLoaded', () => {
    const addressInput = document.getElementById('id_recipient_address');
    const options = {
        componentRestrictions: { country: 'rs' },
        strictBounds: true,
        types: ['address']
    };

    if (addressInput) {
        fetch('http://127.0.0.1:8000/api/v1/get_google_api_key/')
            .then(response => response.json())
            .then(data => {
                const googleApiKey = data.GOOGLE_API_KEY;
                const googleMapsScript = document.createElement('script');
                googleMapsScript.src = `https://maps.googleapis.com/maps/api/js?key=${googleApiKey}&libraries=places`;
                googleMapsScript.defer = true;
                googleMapsScript.onload = () => {
                    const autoComplete = new google.maps.places.Autocomplete(addressInput, options);
                };
                document.head.appendChild(googleMapsScript);
            })
            .catch(error => console.error('Error fetching Google API key:', error));
    }
});
