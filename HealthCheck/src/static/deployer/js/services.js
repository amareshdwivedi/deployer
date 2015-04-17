// JavaScript Document		
jQuery(document).ready(function() {
	$.ajax({
     type: "GET",
     url: "http://localhost:8080/v1/deployer/customers/",
     async: false,
     dataType: "json",
	 success: function(data){
		alert("1");
	 },
	 error: function(request,status,errorThrown){
		 alert("2");
	 }
	});	
});