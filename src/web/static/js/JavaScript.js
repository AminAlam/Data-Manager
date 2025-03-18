// Add debounce function at the top of the file
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

// Add throttle function for operations that need rate limiting but should execute immediately first
function throttle(func, wait) {
  let lastCall = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastCall >= wait) {
      lastCall = now;
      return func.apply(this, args);
    }
  };
}

function put_text(id_parent, id, txt) {     
  document.getElementById(id).value = txt;
  document.getElementById(id_parent).style.display = "none";
  
  // Trigger the input event to update search results
  const inputEvent = new Event('input', { bubbles: true });
  document.getElementById(id).dispatchEvent(inputEvent);
};


function replace_text(id_parent, id, txt) {
  input_txt = document.getElementById(id).value;
  index = input_txt.indexOf(",");
  if (index != -1) {
    input_txt = input_txt.split(",");
    input_txt[input_txt.length-1] = txt;
    for (i = 0; i < input_txt.length; i++) {
      if (input_txt[i] == "") {
        input_txt.splice(i, 1);
      }
    }
    input_txt = input_txt.join(",");
  } else {
    input_txt = txt;
  }
  document.getElementById(id).value = input_txt;
  document.getElementById(id_parent).style.display = "none";
  
  // Trigger the input event to update search results
  const inputEvent = new Event('input', { bubbles: true });
  document.getElementById(id).dispatchEvent(inputEvent);
};


 // make a function called replace_condition_trigger which will be called when the user selects a template name or a method name

 $(document).ready(function(){
  $("#template").change(function(){
    replace_condition("#condition_selected", $("#template").val(), $("#method").val());
  });
  $("#method").change(function(){
    replace_condition("#condition_selected", $("#template").val(), $("#method").val());
  });
});




 function replace_condition(id, template_name, method_name) {
  // Only proceed if we have both values
  if (!template_name || !method_name) return;

  // Cache selectors
  const $element = $(id);
  
  // Empty only once
  $element.empty();

  // Simplified loading indicator
  $element.html("<img src='/static/assets/loading.gif' alt='loading' style='margin-left: auto; margin-right: auto; display: block;'>");

  // Use a fetch API instead of jQuery Ajax for better performance
  fetch("/get_conditoin_by_templatename_methodname", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `template_name=${encodeURIComponent(template_name)}&method_name=${encodeURIComponent(method_name)}`
  })
  .then(response => response.text())
  .then(html => {
    $element.html(html);
  })
  .catch(error => {
    console.error("Error fetching condition:", error);
    $element.html("<p>Error loading condition. Please try again.</p>");
  });
 };



$(document).ready(function(){
    
  // Instead of using a generic approach, let's handle each element individually
  
  // For author_search
  if ($("#author_search").length && $("#author_search_datalist").length) {
    const debouncedAuthorSearch = debounce(function(value) {
      const $datalist = $("#author_search_datalist");
      $datalist.css("display", "block");
      
      // Don't make unnecessary requests for empty inputs
      if (!value.trim()) {
        $datalist.empty();
        return;
      }
      
      fetch("/author_search", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `text=${encodeURIComponent(value)}`
      })
      .then(response => response.json())
      .then(res => {
        let data = "";
        res.forEach(value => {
          data += `<a class='search dropdown-item' onclick='replace_text("author_search_datalist", "author_search", "${value.author}")'>`;
          data += value.author + "</a>";
        });
        $datalist.html(data);
      })
      .catch(error => {
        console.error("Error in author search:", error);
      });
    }, 300); // 300ms debounce
    
    $("#author_search").on("input", function() {
      debouncedAuthorSearch($(this).val());
    });
    
    $(document).click(function(e) {
      if (!$(e.target).is('#author_search') && $("#author_search_datalist").length) {
        $("#author_search_datalist").css("display", "none");
      }
    });
  }
  
  // For tags_search
  if ($("#tags_search").length && $("#tags_search_datalist").length) {
    $("#tags_search").on("input", function(e){
      $("#tags_search_datalist").css("display", "block");
      $("#tags_search_datalist").empty();
      
      $.ajax({
          method: "post",
          url: "/tags_search",
          data: {text: $("#tags_search").val()},
          success: function(res){
              var data = "";
              $.each(res, function(index, value){
                  data += "<a class='search dropdown-item' onclick='put_text(`tags_search_datalist`, `tags_search`, `"+value['tag']+"`)'>";
                  data += value['tag']+"</a>";
              });
              $("#tags_search_datalist").html(data);
          }
      });
    });
    
    $(document).click(function(e) {
      if (!$(e.target).is('#tags_search') && $("#tags_search_datalist").length) {
        $("#tags_search_datalist").css("display", "none");
      }
    });
  }
});


$(document).ready(function(){
  // Only set up the event handler if the element exists
  if ($("#tags_search").length) {
    $("#tags_search").on("input", function(e){
      // Use jQuery to safely access the element
      $("#tags_search_datalist").css("display", "block");
      $("#tags_search_datalist").empty();
      
      $.ajax({
          method: "post",
          url: "/tags_search",
          data: {text: $("#tags_search").val()},
          success: function(res){
              var data = "";
              $.each(res, function(index, value){
                  data += "<a class='search dropdown-item' onclick='put_text(`tags_search_datalist`, `tags_search`, `"+value['tag']+"`)'>";
                  data += value['tag']+"</a>";
              });
              data += "</ul>";
              $("#tags_search_datalist").html(data);
          }
      });
    });
    
    // Use jQuery for the document click handler too
    $(document).click(function(e) {
      if (!$(e.target).is('#tags_search') && $("#tags_search_datalist").length) {
        $("#tags_search_datalist").css("display", "none");
      }
    });
  }
});


$(document).ready(function(){
  if ($("#text_search").length) {
    $("#text_search").on("input", function(e){
      $("#text_search_datalist").css("display", "block");
      $("#text_search_datalist").empty();
      
      $.ajax({
          method: "post",
          url: "/text_search",
          data: {text: $("#text_search").val()},
          success: function(res){
              var data = "";
              $.each(res, function(index, value){
                  data += "<a class='search dropdown-item' onclick='put_text(`text_search_datalist`, `text_search`, `"+value['excerpt']+"`)'>";
                  data += value['excerpt']+"</a>";
              });
              data += "</ul>";
              $("#text_search_datalist").html(data);
          }
      });
    });
    
    $(document).click(function(e) {
      if (!$(e.target).is('#text_search') && $("#text_search_datalist").length) {
        $("#text_search_datalist").css("display", "none");
      }
    });
  }
});



$(document).ready(function(){
  $("#action").change(function(){
    if ($("#action").val() == "set_parent_entry") {
      $("#parent_entry_hash_id").show();
      $("#email_notification_section").hide();
    } else if ($("#action").val() == "notify_by_email") {
      $("#email_notification_section").show();
      $("#parent_entry_hash_id").hide();
    } else {
      $("#parent_entry_hash_id").hide();
      $("#email_notification_section").hide();
    }
  });
});



$(document).ready(function(){
  // Check if element exists before trying to access it
  const dateBoolElement = $("#date_bool");
  if (dateBoolElement.length) {
      dateBoolElement.change(function(){
          if (dateBoolElement.is(":checked")) {
              $("#date_start").prop("disabled", false);
              $("#date_end").prop("disabled", false);
          } else {
              $("#date_start").prop("disabled", true);
              $("#date_end").prop("disabled", true);
          }
      });
  }
});




if (document.getElementById('Files_id')) {
  document.getElementById('Files_id').onchange = function() {
    var fullName = getFileName(document.getElementById('Files_id').value);
    console.log(fullName);
    
    // Check if the element exists before trying to set its innerHTML
    var filesNameElement = document.getElementById("Files_name_id");
    if (filesNameElement) {
      filesNameElement.innerHTML = fullName;
    } else {
      // Use the new file display mechanism instead
      updateFileLabel(this);
    }
  };
}

var getFileName = function(fullPath) {
  if (!fullPath) return null;
  var startIndex = (fullPath.indexOf('\\') >= 0 ? fullPath.lastIndexOf('\\') : fullPath.lastIndexOf('/'));
  var filename = fullPath.substring(startIndex);
  if (filename.indexOf('\\') === 0 || filename.indexOf('/') === 0) {
    return filename.substring(1);
  }
  return null;
};


function copy_2_clipboard(that){
  var inp =document.createElement('input');
  document.body.appendChild(inp)
  inp.value =that.textContent
  inp.select();
  document.execCommand('copy',false);
  inp.remove();
  alert("Copied the text: " + inp.value);
  }

// Initialize dropdown functionality for action buttons
$(document).ready(function(){
  // For Bootstrap 5, we need to use the bootstrap object directly
  // Initialize dropdowns if Bootstrap 5 is available
  if (typeof bootstrap !== 'undefined') {
    // Initialize all dropdowns using Bootstrap 5 syntax
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
    var dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
      return new bootstrap.Dropdown(dropdownToggleEl);
    });
  }
  
  // Handle file selection for multiple files
  if (document.getElementById('Files_id')) {
    document.getElementById('Files_id').addEventListener('change', function(e) {
      var fileNames = [];
      for (var i = 0; i < this.files.length; i++) {
        fileNames.push(this.files[i].name);
      }
      
      var label = document.getElementById('Files_name_id');
      if (label) {
        if (fileNames.length > 1) {
          label.textContent = fileNames.length + ' files selected';
        } else if (fileNames.length === 1) {
          label.textContent = fileNames[0];
        } else {
          label.textContent = 'Choose file(s)';
        }
      }
    });
  }
  
  // Update file input label with selected filenames
  window.updateFileLabel = function(input) {
    const selectedFilesDiv = document.getElementById('selected-files');
    const alertDiv = document.getElementById('file-alert');
    
    // Create elements if they don't exist
    if (!selectedFilesDiv) {
      const filesSection = input.closest('.card-body');
      if (filesSection) {
        const newSelectedFilesDiv = document.createElement('div');
        newSelectedFilesDiv.id = 'selected-files';
        newSelectedFilesDiv.className = 'mt-2';
        filesSection.appendChild(newSelectedFilesDiv);
      } else {
        console.log("Could not find parent card-body for file display");
        return;
      }
    }
    
    if (!alertDiv) {
      const filesSection = input.closest('.card-body');
      if (filesSection) {
        const newAlertDiv = document.createElement('div');
        newAlertDiv.id = 'file-alert';
        newAlertDiv.className = 'alert alert-info';
        newAlertDiv.innerHTML = '<i class="bi bi-info-circle me-2"></i>No files selected';
        
        // Insert at the beginning of the section
        if (filesSection.firstChild) {
          filesSection.insertBefore(newAlertDiv, filesSection.firstChild);
        } else {
          filesSection.appendChild(newAlertDiv);
        }
      }
    }
    
    // Now get the elements (they should exist now)
    const selectedFilesDivUpdated = document.getElementById('selected-files');
    const alertDivUpdated = document.getElementById('file-alert');
    
    if (!selectedFilesDivUpdated || !alertDivUpdated) {
      console.log("Could not create required elements for file display");
      return;
    }
    
    if (input.files && input.files.length > 0) {
      alertDivUpdated.style.display = 'none';
      selectedFilesDivUpdated.innerHTML = '';
      
      for (let i = 0; i < input.files.length; i++) {
        const file = input.files[i];
        const fileItem = document.createElement('div');
        fileItem.className = 'alert alert-secondary d-flex justify-content-between align-items-center mb-2';
        
        // Format file size
        let fileSize;
        if (file.size > 1024 * 1024) {
          fileSize = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
        } else {
          fileSize = (file.size / 1024).toFixed(2) + ' KB';
        }
        
        fileItem.innerHTML = `
          <div>
            <i class="bi bi-file-earmark me-2"></i>${file.name}
            <span class="text-muted ms-2">(${fileSize})</span>
          </div>
        `;
        selectedFilesDivUpdated.appendChild(fileItem);
      }
      
      console.log(`${input.files.length} files selected`);
    } else {
      alertDivUpdated.style.display = 'block';
      selectedFilesDivUpdated.innerHTML = '';
      console.log('No files selected');
    }
  };
});

// Username search for email notifications
$(document).ready(function(){
  const usernameInput = $("#adress_for_notify_by_email");
  const suggestionsList = $("#username_suggestions");
  
  if (usernameInput.length) {
    // When typing in the username field
    usernameInput.on("input", function() {
      const query = $(this).val();
      const lastQuery = query.split(',').pop().trim();
      
      if (lastQuery.length < 1) {
        suggestionsList.hide();
        return;
      }
      
      // Make AJAX request to search for usernames
      $.ajax({
        url: "/username_search",
        method: "POST",
        data: { text: lastQuery },
        success: function(response) {
          if (response.length > 0) {
            // Build suggestions list
            let html = '';
            response.forEach(function(user) {
              html += `<a class="dropdown-item" href="#" data-username="${user[0]}">${user[0]}</a>`;
            });
            
            suggestionsList.html(html);
            suggestionsList.show();
            
            // Handle clicking on a suggestion
            $(".dropdown-item", suggestionsList).on("click", function(e) {
              e.preventDefault();
              const username = $(this).data("username");
              
              // Get current input value and replace the last part
              let currentValue = usernameInput.val();
              const parts = currentValue.split(',');
              parts.pop(); // Remove the last part (what user was typing)
              
              // Add the selected username
              if (parts.length > 0) {
                currentValue = parts.join(',') + ', ' + username;
              } else {
                currentValue = username;
              }
              
              usernameInput.val(currentValue + ', ');
              suggestionsList.hide();
              usernameInput.focus();
            });
          } else {
            suggestionsList.hide();
          }
        }
      });
    });
    
    // Hide suggestions when clicking outside
    $(document).on("click", function(e) {
      if (!$(e.target).closest("#adress_for_notify_by_email, #username_suggestions").length) {
        suggestionsList.hide();
      }
    });
  }
});


$(document).ready(function(){
  if ($("#title_search").length) {
    $("#title_search").on("input", function(e){
      $("#title_search_datalist").css("display", "block");
      $("#title_search_datalist").empty();
      
      $.ajax({
          method: "post",
          url: "/title_search",
          data: {text: $("#title_search").val()},
          success: function(res){
              var data = "";
              $.each(res, function(index, value){
                  data += "<a class='search dropdown-item' onclick='put_text(`title_search_datalist`, `title_search`, `"+value[0]+"`)'>";
                  data += value[0]+"</a>";
              });
              data += "</ul>";
              $("#title_search_datalist").html(data);
          }
      });
    });
    
    $(document).click(function(e) {
      if (!$(e.target).is('#title_search') && $("#title_search_datalist").length) {
        $("#title_search_datalist").css("display", "none");
      }
    });
  }
});

// Optimized notification handling system
// Global notification state
const notificationState = {
  etag: null,
  lastCount: 0,
  interval: null,
  isPollingActive: true,
  isVisible: !document.hidden,
  pendingRequest: false,
  errorCount: 0,   // Add an error counter
  maxErrors: 5     // Maximum consecutive errors before disabling auto-refresh
};

function loadNotifications() {
  // Skip if another request is in progress or tab is hidden
  if (notificationState.pendingRequest || !notificationState.isVisible) {
    return;
  }
  
  // Skip if we've had too many consecutive errors
  if (notificationState.errorCount >= notificationState.maxErrors) {
    console.warn('Notification polling disabled due to consecutive errors');
    if (notificationState.interval) {
      clearInterval(notificationState.interval);
      notificationState.interval = null;
    }
    return;
  }
  
  notificationState.pendingRequest = true;
  
  // Prepare fetch options with conditional header if we have an ETag
  const fetchOptions = {
    method: 'GET',
    headers: {},
    // Add timeout to prevent hanging requests
    signal: AbortSignal.timeout(10000) // 10 seconds timeout
  };
  
  if (notificationState.etag) {
    fetchOptions.headers['If-None-Match'] = notificationState.etag;
  }
  
  fetch('/api/notifications/unread', fetchOptions)
    .then(response => {
      // Reset error counter on successful response
      notificationState.errorCount = 0;
      
      // Store the new ETag if provided
      const newEtag = response.headers.get('ETag');
      if (newEtag) {
        notificationState.etag = newEtag;
      }
      
      // If response is 304 Not Modified, no need to process data
      if (response.status === 304) {
        return { notifications: [] };
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      return response.json();
    })
    .then(data => {
      const notifications = data.notifications || [];
      const $notificationList = $('#notificationList');
      const $badge = $('.notification-badge');
      
      // Only update DOM if notification count has changed
      if (notificationState.lastCount !== notifications.length || $notificationList.children().length === 0) {
        notificationState.lastCount = notifications.length;
        
        // Use document fragment for efficient DOM operations
        const fragment = document.createDocumentFragment();
        
        if (notifications.length > 0) {
          $badge.text(notifications.length).show();
          
          notifications.forEach(function(notification) {
            const li = document.createElement('li');
            li.innerHTML = `
              <a href="#" class="dropdown-item notification-item" 
                data-notification-id="${notification.id}"
                onclick="event.preventDefault();">
                  <div class="notification-message">${notification.message}</div>
                  <div class="notification-time">
                      <small class="text-muted">From: ${notification.author}</small>
                      <small class="text-muted float-end">${new Date(notification.date).toLocaleString()}</small>
                  </div>
              </a>
            `;
            fragment.appendChild(li);
          });
          
          // Clear and append in one operation
          $notificationList.empty()[0].appendChild(fragment);
        } else {
          $badge.hide();
          $notificationList.html('<li><span class="dropdown-item text-muted">No new notifications</span></li>');
        }
      }
    })
    .catch(error => {
      console.error('Error loading notifications:', error);
      // Increment error counter
      notificationState.errorCount++;
      
      // If we've had multiple errors, slow down the polling
      if (notificationState.errorCount > 2 && notificationState.interval) {
        clearInterval(notificationState.interval);
        notificationState.interval = setInterval(loadNotifications, 60000); // Increase to 60 seconds
      }
    })
    .finally(() => {
      notificationState.pendingRequest = false;
    });
}

// Use a throttled version for initialization to prevent excessive calls
const throttledLoadNotifications = throttle(loadNotifications, 2000);

// Update visibility state when tab visibility changes
document.addEventListener('visibilitychange', function() {
  notificationState.isVisible = !document.hidden;
  
  if (document.hidden) {
    // Tab is hidden, clear interval to save resources
    if (notificationState.interval) {
      clearInterval(notificationState.interval);
      notificationState.interval = null;
    }
    notificationState.isPollingActive = false;
  } else {
    // Tab is visible again, check for notifications immediately
    // and restart polling
    if (!notificationState.isPollingActive) {
      loadNotifications();
      notificationState.interval = setInterval(loadNotifications, 30000);
      notificationState.isPollingActive = true;
    }
  }
});

// Optimized notification click handler using event delegation
$(document).on('click', '.notification-item', function(e) {
  e.preventDefault();
  const $this = $(this);
  const notificationId = $this.data('notification-id');
  
  // Prevent duplicate clicks
  if ($this.hasClass('processing')) {
    return;
  }
  
  $this.addClass('processing');
  
  fetch('/api/notifications/mark-read', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ id: notificationId })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to mark notification as read');
    }
    return response.json();
  })
  .then(() => {
    $this.removeClass('unread');
    loadNotifications();
  })
  .catch(error => {
    console.error('Error marking notification as read:', error);
  })
  .finally(() => {
    $this.removeClass('processing');
  });
});

// Initialize notification system
$(document).ready(function() {
  try {
    // Load notifications after a slight delay to ensure page is fully loaded
    setTimeout(() => {
      throttledLoadNotifications();
      
      // Set up interval for polling with a more conservative interval
      if (!notificationState.interval && notificationState.isVisible) {
        notificationState.interval = setInterval(loadNotifications, 30000); // Refresh every 30 seconds
      }
    }, 1000);
    
    // Pause polling when dropdown is open (user is viewing notifications)
    $('.notification-dropdown').parent().on('shown.bs.dropdown', function() {
      if (notificationState.interval) {
        clearInterval(notificationState.interval);
        notificationState.interval = null;
      }
    });
    
    // Resume polling when dropdown is closed
    $('.notification-dropdown').parent().on('hidden.bs.dropdown', function() {
      if (!notificationState.interval && notificationState.isVisible) {
        notificationState.interval = setInterval(loadNotifications, 30000);
      }
    });
  } catch (e) {
    console.error('Error initializing notification system:', e);
  }
});

// Optimized load more results functionality
$(document).ready(function() {
  let currentOffset = 10; // Start after the first 10 entries
  let isLoadingMore = false;
  
  $("#loadMoreResults").on("click", function() {
    // Prevent multiple simultaneous requests
    if (isLoadingMore) return;
    
    const button = $(this);
    button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...');
    isLoadingMore = true;
    
    fetch('/load_more_entries?offset=' + currentOffset)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(response => {
        if (response.entries && response.entries.length > 0) {
          // Use document fragment for better performance
          const tableBody = document.querySelector('table tbody');
          const fragment = document.createDocumentFragment();
          
          response.entries.forEach(function(entry) {
            const row = document.createElement('tr');
            row.innerHTML = `
              <td class="text-center"><input type="checkbox" name="selected_entries" value="${entry.id}" class="form-check-input entry-checkbox"></td>
              <td><a href="/entry/${entry.id}">${entry.title || 'Untitled'}</a></td>
              <td>${entry.hash_id || ''}</td>
              <td>${entry.date || ''}</td>
              <td>${entry.author || ''}</td>
              <td>${entry.tags || ''}</td>
              <td>${entry.conditions || ''}</td>
            `;
            fragment.appendChild(row);
          });
          
          // Append all rows in one operation
          tableBody.appendChild(fragment);
          
          // Update the offset for the next load
          currentOffset = response.next_offset;
          
          // Hide the button if there are no more entries
          if (!response.has_more) {
            button.hide();
          }
        } else {
          button.hide();
        }
      })
      .catch(error => {
        console.error('Error loading more results:', error);
        alert('Error loading more results. Please try again.');
      })
      .finally(() => {
        button.prop('disabled', false).html('<i class="bi bi-arrow-down-circle me-1"></i> Show More Results');
        isLoadingMore = false;
      });
  });
});