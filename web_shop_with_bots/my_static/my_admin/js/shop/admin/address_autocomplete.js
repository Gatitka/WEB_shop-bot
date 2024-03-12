document.addEventListener('DOMContentLoaded', () => {
    const addressInput = document.getElementById('id_recipient_address');
    const options = {
        componentRestrictions: { country: 'rs' },
        strictBounds: true,
        types: ['address']
    };

    if (addressInput) {
        const googleMapsScript = document.createElement('script');
        googleMapsScript.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_API_KEY}&libraries=places`;
        googleMapsScript.defer = true;

        googleMapsScript.onload = () => {
            const autoComplete = new google.maps.places.Autocomplete(addressInput, options);
        };

        document.head.appendChild(googleMapsScript);
    }
});
