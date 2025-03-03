function put_text(id_parent, id, txt) {     
  document.getElementById(id).value = txt;
  document.getElementById(id_parent).style.display = "none";

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
    console.log(input_txt)
    input_txt = input_txt.join(",");
  } else {
    input_txt = txt;
  }
  document.getElementById(id).value = input_txt;

  document.getElementById(id_parent).style.display = "none";

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

    // load /static/loading.gif while the ajax request is being processed

    $(id).empty();

    var condition_html = "<img src='/static/assets/loading.gif' alt='loading' style='margin-left: auto; margin-right: auto; display: block;'>";
    $(id).html(condition_html);

    // make an ajax request to the server to get the condition html
      $.ajax({
          method:"post",
          url:"/get_conditoin_by_templatename_methodname",
          data:{template_name:template_name, method_name:method_name},
          success:function(res){
              $(id).empty();
              condition_html = res;
              $(id).html(condition_html);
          },
          error:function(err){
              console.log(err);
          }
      });
 };



$(document).ready(function(){
    
  // Instead of using a generic approach, let's handle each element individually
  
  // For author_search
  if ($("#author_search").length && $("#author_search_datalist").length) {
    $("#author_search").on("input", function(e){
      $("#author_search_datalist").css("display", "block");
      $("#author_search_datalist").empty();
      $.ajax({
          method:"post",
          url:"/author_search",
          data:{text:$("#author_search").val()},
          success:function(res){
              var data = "";
              $.each(res,function(index,value){
                  data += "<a class='search dropdown-item' onclick='put_text(`author_search_datalist`, `author_search`, `"+value[0]+"`)'>";
                  data += value[0]+"</a>";
              });
              data += "</ul>";
              $("#author_search_datalist").html(data);
          }
      });
    });
    
    $(document).click(function(e) {
      if (!$(e.target).is('#author_search') && $("#author_search_datalist").length) {
        $("#author_search_datalist").css("display", "none");
      }
    });
  }
  
  // Similar checks for other elements
  // ...
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
                  data += "<a class='search dropdown-item' onclick='replace_text(`tags_search_datalist`, `tags_search`, `"+value[0]+"`)'>";
                  data += value[0]+"</a>";
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
                  data += "<a class='search dropdown-item' onclick='put_text(`text_search_datalist`, `text_search`, `"+value[0]+"`)'>";
                  data += value[0]+"</a>";
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
    
    if (!selectedFilesDiv || !alertDiv) {
      console.log("Required elements not found for file display");
      return;
    }
    
    if (input.files && input.files.length > 0) {
      alertDiv.style.display = 'none';
      selectedFilesDiv.innerHTML = '';
      
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
        selectedFilesDiv.appendChild(fileItem);
      }
      
      console.log(`${input.files.length} files selected`);
    } else {
      alertDiv.style.display = 'block';
      selectedFilesDiv.innerHTML = '';
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