document.addEventListener('DOMContentLoaded', function() {
  // Check if formset exists (editable items are present)
  var formset = document.getElementById('changelist-form');
  var hasEditableFields = false;

  if (formset) {
      // Look for any editable fields (inputs, selects) in the form
      var editableFields = formset.querySelectorAll('input:not([type="hidden"]), select:not([name="action"])');
      hasEditableFields = editableFields.length > 0;
  }

  // Only add the save button if there are editable fields
  if (hasEditableFields) {
      // Find the actions div
      var actionsDiv = document.querySelector('.actions');

      if (actionsDiv) {
          // Create a container for the buttons to properly organize the layout
          var buttonContainer = document.createElement('div');
          buttonContainer.style.cssText = 'display: flex; align-items: center; margin-left: auto;';

          // Get the existing button (if any)
          var existingButton = actionsDiv.querySelector('button[name="index"]');
          if (existingButton) {
              // Clone the existing button to the container
              var goButton = existingButton.cloneNode(true);
              buttonContainer.appendChild(goButton);

              // Hide the original button
              existingButton.style.display = 'none';

              // Make sure the cloned button works
              goButton.addEventListener('click', function(e) {
                  e.preventDefault();
                  existingButton.click();
              });
          }

          // Create save button - using input type=submit to match Django styling
          var saveButton = document.createElement('input');
          saveButton.id = 'save-action-button';
          saveButton.type = 'button';
          saveButton.className = 'default';
          saveButton.value = 'Сохранить';
          saveButton.style.marginLeft = '10px';

          // Add click event to save button
          saveButton.addEventListener('click', function() {
              var realSaveButton = document.querySelector('#changelist-form input[name="_save"]');
              if (realSaveButton) {
                  realSaveButton.click();
              }
          });

          // Add the button to the container
          buttonContainer.appendChild(saveButton);

          // Add the container to the actions div
          actionsDiv.appendChild(buttonContainer);

          // Reset the layout of the actions div
          actionsDiv.style.cssText = 'display: flex; align-items: center; padding: 5px 0;';
      }
  }
});
