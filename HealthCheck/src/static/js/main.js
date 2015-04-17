// JavaScript Document		
jQuery(document).ready(function() {
	
//===== MESSAGES =====//
			//Alert
		$("div.msgbar").click(function(){
			$(this).slideUp();
		});
		
//===== FORM ELEMENTS =====//
		$("select, input:checkbox, input:radio").uniform(); 
	
//===== FILE UPLOADER =====//
		// <![CDATA[
		  $('#file_upload').uploadify({
			'uploader'  : './uploadify/uploadify.swf',
			'script'    : './uploadify/uploadify.php',
			'cancelImg' : './uploadify/cancel.png',
			'folder'    : './uploads',
			'fileExt'   : '*.jpg;*.gif;*.png',
			'multi'     : true,
			'sizeLimit' : 400000
		  });
		// ]]>
		
//===== JQUERY UI =====//
			/*Progress Bar*/
			$( "#progressbar" ).progressbar({
				value: 37
			});
			
			
			/*Tabs*/
			
			$( "#tabs" ).tabs();
			
			
//===== MODAL WINDOW =====//
			function modal(){
			$('#myModal').modal();
			}
			
//===== jQUERY DATA TABLE =====//			
			oTable = $('#jqtable').dataTable({
					"bJQueryUI": true,
					"sPaginationType": "full_numbers"
			});
			
//===== RESPONSIVE NAV =====//	
	jQuery(".res_icon").toggle(function() {
		 $('#responsive_nav').slideDown(300);	
		 }, function(){
		 $('#responsive_nav').slideUp(300);		 
	});	
		

//===== Manish JS =====//

	/*$('.chooseCustomerType input:radio').click(function() {
		if ($(this).val() === 'Existing Customer') {
			{
				$("#selectExisting").show();
				$("#createNewCustomer").hide();
				$("#quick_actions").show();	
				$(".existingCustomerBtn").show();
				$(".createNewCustomerBtn").hide();
			}
		} else if ($(this).val() === 'Create New Customer') {
		  {
				$("#selectExisting").hide();
				$("#createNewCustomer").show();
				$("#quick_actions").show();	
				$(".existingCustomerBtn").hide();
				$(".createNewCustomerBtn").show();
			}
		} 
	 });	*/
	 
	 $(".createCustomerLink").click(function(){
		 $('#createNewCustomerModel').modal();
         $("#createNewCustomerModel .modal-body .form_fields_container").show();
		 $(".createCustomer-form .form_input").removeClass("error");
         $("#createNewCustomerModel .modal-body .sucessMsg").hide();
         $(".createNewCustomerBtn").show();
         $("#createNewCustomerModel .cancelButton").hide();
		$(".errorMsg").hide();
	 });

    $("#healthCheckConfigurationModel .modal-content").hide();
    $(".editCheck").click(function(){
        var checkerType = $(this).attr("name");
        if($(this).attr('disabled')){
            return false;
        }else{
            $('#healthCheckConfigurationModel').modal();
            $("#healthCheckConfigurationModel .modal-content").hide();
            $("#healthCheckConfigurationModel .statusmessage").hide();
            $("#healthCheckConfigurationModel .modal-content .formTbl").show();
            $("#healthCheckConfigurationModel .cancelButton").hide();
            $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").show();
            if(checkerType == "vc"){
                $(".modal-content#modal_vc").show();
                $(".modal-content#modal_ncc").hide();
                $(".modal-content#modal_view").hide();
            }else if(checkerType == "ncc"){
                $(".modal-content#modal_vc").hide();
                $(".modal-content#modal_ncc").show();
                $(".modal-content#modal_view").hide();
            }else if(checkerType == "view"){
                $(".modal-content#modal_vc").hide();
                $(".modal-content#modal_ncc").hide();
                $(".modal-content#modal_view").show();
            }
        }
	});

    
    
	 $(".createTaskLink").click(function(){
		 $('#createTaskModal').modal();
		 $(".createTask-form .form_input").removeClass("error");
		 $(".errorMsg").hide();
	 });
	 
	 jQuery(".antiscroll-inner").niceScroll();
	 
	 $("#mainTabContainer").tabs({
          disabled: [1,2,3,4]
        });
	 
    /*Predeployer Tabs Functionlity start*/
	$('#preDeploy_secondaryNav ul li').each(function(i, e){
		$("a", this).attr("class", "step-" + i);
	});
	$(".preDeploy_maincontent .quick_actions").each(function(i, e){
		$(".next", this).attr("name", "step-" + (i+1));
	});
	$(".preDeploy_maincontent .quick_actions").each(function(i, e){
		$(".back", this).attr("name", "step-" + (i-1));
	});
	
	$(".preDeploy_maincontent a.next").click(function(event) {
        var isFormValid = true;
        var currentContainer = $(this).parents().eq(1).find(".mainBody_container input.required");
        var ipCheck = $(this).parents().eq(1).find(".mainBody_container input.required.ipcheck");
        //var ipRegex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        var ipRegex=/^(?!0)(?!.*\.$)((1?\d?\d|25[0-5]|2[0-4]\d)(\.|$)){4}$/;
        
        currentContainer.each(function(index, value){
			if ($.trim($(value).val()).length == 0){
				$(value).addClass("error");
			} else {
				$(value).removeClass("error");
			}
        });
        ipCheck.each(function(index, value){
			if (!($(value).val()).match(ipRegex)){
				$(value).addClass("error");
			} else {
				$(value).removeClass("error");
			}
        });
        var errorInput = $(this).parents().eq(1).find(".mainBody_container input.error");
        if(errorInput.length > 0){
            $(this).parents().eq(1).find(".errorMsg").show();
            $(this).parents().eq(1).find(".errorMsg").html("Please fill in all the required fields (highlighted in red)");
            isFormValid = false;
        }else{
            $(this).parents().eq(1).find(".errorMsg").hide();
            $(this).parents().eq(1).find(".errorMsg").html("");
            isFormValid = true;
        }
        
        if(isFormValid ){
            var nextStep = $(this).attr("name");
            event.preventDefault();
            $("#preDeploy_secondaryNav ul li").find("."+nextStep+"").parent().removeClass("disabled");
            $("#preDeploy_secondaryNav ul li a."+nextStep+"").parent().siblings().addClass("disabled");
            $("#preDeploy_secondaryNav ul li a."+nextStep+"").parent().addClass("active");
            $("#preDeploy_secondaryNav ul li a."+nextStep+"").parent().siblings().removeClass("active");
            var tab = $("#preDeploy_secondaryNav ul li a."+nextStep+"").attr("href");
            $(".tab-content").not(tab).css("display", "none");
            $(tab).fadeIn();
            $(tab).addClass(nextStep);
        }
    });
	$(".preDeploy_maincontent a.back").click(function(event) {
		var previousStep = $(this).attr("name");
		event.preventDefault();
		$("#preDeploy_secondaryNav ul li").find("."+previousStep+"").parent().removeClass("disabled");
		$("#preDeploy_secondaryNav ul li a."+previousStep+"").parent().siblings().addClass("disabled");
		$("#preDeploy_secondaryNav ul li a."+previousStep+"").parent().addClass("active");
        $("#preDeploy_secondaryNav ul li a."+previousStep+"").parent().siblings().removeClass("active");
        var tab = $("#preDeploy_secondaryNav ul li a."+previousStep+"").attr("href");
        $(".tab-content").not(tab).css("display", "none");
        $(tab).fadeIn();
		$(tab).addClass(previousStep);
    });
	$("#preDeploy_secondaryNav ul li.disabled a").unbind('click');
	/*Predeployer tab functionality end*/
	
    /*Predeloyer Add/Remove Block functionality starts*/
	var count = 1;
	if(count <= 1){
			$('.removeBlock').hide();
	}
	
	$('.addBlock').live("click",function(){
		var $clone = $('#block-1').clone();
		//$clone.find('[id]').each(function(){this.id+='someotherpart'});
		$clone.attr('id', "block-"+(++count));
		$clone.insertAfter($('[id^=block]:last'));
		$("#block-"+count+"").find(".blockName").html("Block "+count+"");
        
        $("#block-"+count+"").find(".accordion-section-title").removeAttr("href").attr("href", "#accordion-"+count+"");
        $("#block-"+count+"").find(".accordion-section-content").removeAttr("id").attr("id", "accordion-"+count+"");
		$('.removeBlock').show();
	});
	$(".removeBlock").live("click",function(){
		$(this).parents().eq(2).remove();
		count--;
		if(count <= 1){
			$('.removeBlock').hide();
		}
	});
    /*Predeployer Add/Remove block functionality Ends*/
	
    /*Blocks Expand /Collapse Funtionality Start*/
    $('.accordion-section-title.plus').live("click",function(e) {
        var currentAttrValue = $(this).attr('href');
        $(this).find("i").removeClass('fa-plus-square').addClass('fa-minus-square');
        $(this).addClass('active minus').removeClass('plus');
        $(currentAttrValue).slideDown(300).addClass('open'); 
        e.preventDefault();
    });
    
    $('.accordion-section-title.minus').live("click",function(e) {
        var currentAttrValue = $(this).attr('href');
        $(this).find("i").addClass('fa-plus-square').removeClass('fa-minus-square');
        $(this).removeClass('active minus').addClass('plus');
        $(currentAttrValue).slideUp(300).removeClass('open'); 
        e.preventDefault();
    });
    /*Blocks Expand/Collapse Functionality Ends*/    
    
    /*Create new Tesk*/
    
    $(".createNewTaskBtn").live("click",function(){
        var taskType = $("#task_name").val();
        if(taskType == "healthcheck"){
            $( "#mainTabContainer" ).tabs("enable", 3).tabs("select", 3);
        }else if(taskType == "deployment"){
            $( "#mainTabContainer" ).tabs("enable", 1).tabs("select", 1);
        }        
        $('#createTaskModal').modal('hide');
	});
    
    $('#task_name').on('change', function() {
        if(this.value == "healthcheck"){
            $("li.importFile").hide();
        }else if(this.value == "deployment"){
            $("li.importFile").show();
        }  
    })
});