
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


 function replace_condition(id, template_name) {

      $.ajax({
          method:"post",
          url:"/get_conditoin_by_templatename",
          data:{template_name:template_name},
          success:function(res){
              $(id).empty();
              condition_html = res;
              $(id).html(condition_html);
          },
          error:function(err){
              console.log(err);
          }
      });
      $(document).click(function(e) {
    if (!$(e.target).is('#author_search')) {
      document.getElementById('author_search_datalist').style.display = "none";
    }
  });
 };



$(document).ready(function(){
    
  $("#author_search").on("input",function(e){
    document.getElementById('author_search_datalist').style.display = "block";
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
    if (!$(e.target).is('#author_search')) {
      document.getElementById('author_search_datalist').style.display = "none";
    }
  });
});


$(document).ready(function(){
  
  $("#tags_search").on("input",function(e){
    document.getElementById('tags_search_datalist').style.display = "block";
      $("#tags_search_datalist").empty();
      $.ajax({
          method:"post",
          url:"/tags_search",
          data:{text:$("#tags_search").val()},
          success:function(res){
              var data = "";
              $.each(res,function(index,value){
                  data += "<a class='search dropdown-item' onclick='replace_text(`tags_search_datalist`, `tags_search`, `"+value[0]+"`)'>";
                  data += value[0]+"</a>";
              });
              data += "</ul>";
              $("#tags_search_datalist").html(data);
          }
      });
  });
  $(document).click(function(e) {
    if (!$(e.target).is('#tags_search')) {
      document.getElementById('tags_search_datalist').style.display = "none";
    }
  });
});


$(document).ready(function(){

  $("#text_search").on("input",function(e){
    document.getElementById('text_search_datalist').style.display = "block";
      $("#text_search_datalist").empty();
      $.ajax({
          method:"post",
          url:"/text_search",
          data:{text:$("#text_search").val()},
          success:function(res){
              var data = "";
              $.each(res,function(index,value){
                  data += "<a class='search dropdown-item' onclick='put_text(`text_search_datalist`, `text_search`, `"+value[0]+"`)'>";
                  data += value[0]+"</a>";
              });
              data += "</ul>";
              $("#text_search_datalist").html(data);
          }
      });
  });
  $(document).click(function(e) {
    if (!$(e.target).is('#text_search')) {
      document.getElementById('text_search_datalist').style.display = "none";
    }
  });
});



$(document).ready(function(){
  $("#action").change(function(){
    if ($("#action").val() == "set_parent_experiment") {
      $("#parent_experiment_hash_id").show();
    } else {
      $("#parent_experiment_hash_id").hide();
    }
  });
});



$(document).ready(function(){
  $("#date_bool").change(function(){
    if ($("#date_bool").is(":checked")) {
      $("#date_start").prop("disabled", false);
      $("#date_end").prop("disabled", false);
    } else {
      $("#date_start").prop("disabled", true);
      $("#date_end").prop("disabled", true);
    }
  });
});




if (document.getElementById('Files_id')) {
  document.getElementById('Files_id').onchange = function() {
    var fullName = getFileName(document.getElementById('Files_id').value);
    console.log(fullName);
    document.getElementById("Files_name_id").innerHTML= fullName;
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


// make a function called copyToClipboard that takes one argument, text and copies it to the clipboard
function copy_2_clipboard(that){
  var inp =document.createElement('input');
  document.body.appendChild(inp)
  inp.value =that.textContent
  inp.select();
  document.execCommand('copy',false);
  inp.remove();
  alert("Copied the text: " + inp.value);
  }