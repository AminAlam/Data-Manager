document.addEventListener("DOMContentLoaded", function() {
    showEmailDate('email_date', document.getElementById('emailed'));
  });

// function showEmailDate(divId, element)
// {
//     document.getElementById(divId).style.display = element.value == "Yes" ? 'block' : 'none';
// }



function put_text(id_parent, id, txt) {     
  document.getElementById(id).value = txt;
  document.getElementById(id_parent).style.display = "none";

 };


 function replace_text(id_parent, id, txt) {
  input_txt = document.getElementById(id).value;
  // find index of , in input_txt
  index = input_txt.indexOf(",");
  // if index is not -1, then there is a comma in the string
  if (index != -1) {
    // split the string by ,
    input_txt = input_txt.split(",");
    // replace the last part with the new text
    input_txt[input_txt.length-1] = txt;
    // iterate through input_txt
    for (i = 0; i < input_txt.length; i++) {
      // if the part is empty, remove it
      if (input_txt[i] == "") {
        input_txt.splice(i, 1);
      }
    }
    // join the parts back together
    console.log(input_txt)
    input_txt = input_txt.join(",");
  } else {
    // if there is no comma, then just add the new text
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
});