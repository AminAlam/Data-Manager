document.addEventListener("DOMContentLoaded", function() {
    showEmailDate('email_date', document.getElementById('emailed'));
  });

// function showEmailDate(divId, element)
// {
//     document.getElementById(divId).style.display = element.value == "Yes" ? 'block' : 'none';
// }


$(document).ready(function(){
    
  $("#author_search").on("input",function(e){
      $("#author_search_datalist").empty();
      $.ajax({
          method:"post",
          url:"/author_search",
          data:{text:$("#author_search").val()},
          success:function(res){
              var data = "";
              $.each(res,function(index,value){
                  data += "<a class='search dropdown-item ' href=/"+value[-1]+">";
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
      $("#tags_search_datalist").empty();
      $.ajax({
          method:"post",
          url:"/tags_search",
          data:{text:$("#tags_search").val()},
          success:function(res){
              var data = "";
              $.each(res,function(index,value){
                  data += "<a class='search dropdown-item ' href=/"+value[-1]+">";
                  data += value[0]+"</a>";
              });
              data += "</ul>";
              $("#tags_search_datalist").html(data);
          }
      });
  });
});