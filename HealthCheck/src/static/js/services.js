// JavaScript Document		
jQuery(document).ready(function() {
    getCustomers();

    function getCustomers() {
        $.ajax({
            type: "GET",
            url: "/v1/deployer/customers/",
            async: false,
            dataType: "json",
            success: function(data) {
                var customers = '';

                if (data.response != 404 || data.response != '404') {
                    for (var i = 0; i < data.customer_record.length; i++) {
                        customers += '<tr><td class="customerId">' + data.customer_record[i].customer_id + '</td><td class="customerName">' + data.customer_record[i].customer_name + '</td></tr>';
                    }

                    $("table.customersTable tbody").html(customers);

                }
            },
            error: function(request, status, errorThrown) {
                alert("No Data Available");
            }
        });
    }

    function getCutomerDetails(customerId) {
        $.ajax({
            type: "GET",
            url: "/v1/deployer/customers/" + customerId + "/",
            async: false,
            dataType: "json",
            success: function(data) {
                $(".customerDetails").show();
                 $("a.kickoffBtn").hide();
                $(".customerDetails h3 span").html(data.customer_record[0].customer_name);
                $("table.customersDetailsTable tbody tr:gt(0)").remove();
                var customerDetail = '';
                if(data.customer_history.length != 0){
                    $("table.customersDetailsTable tbody tr.noData").hide();
                    for (var i = 0; i < data.customer_history.length; i++) {
                        customerDetail += '<tr><td class="id">' + data.customer_history[i].id + '</td><td class="task">' + data.customer_history[i].task + '</td><td class="status">' + data.customer_history[i].status + '</td><td class="date_created">' + data.customer_history[i].date_created + '</td></tr>';
                    }
                    $("table.customersDetailsTable tbody").append(customerDetail);
                }else{
                    $("table.customersDetailsTable tbody tr.noData").show();
                }
                
            },
            error: function(request, status, errorThrown) {
                alert("No Data Available");
            }
        });
    }
    
    function getCustomerReports(customerId) {
        $( "#mainTabContainer" ).tabs("enable", 4);
        $.ajax({
            type: "GET",
            url: "../reports/" + customerId + "/",
            async: false,
            dataType: "json",
            success: function(data) {
                var customerDetail = '';
                $("table.reportTable tbody tr:gt(0)").remove();
                if(data.customer_reports.length != 0){
                    $("table.reportTable tbody tr.noData").hide();
                    for (var i = 0; i < data.customer_reports.length; i++) {
                       customerDetail += '<tr><td class="filename"><a href="'+data.customer_reports[i].filename+'">' + data.customer_reports[i].filename + '</a></td><td class="datecreate">' + data.customer_reports[i].date_created + '</td><td class="downloadIcon"><a href="'+data.customer_reports[i].filename+'"><span class="fa fa-file-pdf-o fa-6"></span></a></td></tr>';
                    }
                    $("table.reportTable tbody").append(customerDetail);
                }else{
                    $("table.reportTable tbody tr.noData").show();
                }
            },
            error: function(request, status, errorThrown) {
                alert("No Data Available");
            }
        });
    }

    $(".customersTable tbody").on('click', 'tr', function() {
        $(".customersTable tbody tr").removeClass("row_selected");
        $(this).addClass("row_selected");
        var customerId = $(this).find('td.customerId').html();
        $("#customerId").val(customerId);
        getCutomerDetails(customerId);
        getCustomerReports(customerId);
    });

    $(".createNewCustomerBtn").click(function() {
        var isFormValid = true;
        $(".createCustomer-form .form_input input").each(function(index, value) {
            if ($.trim($(value).val()).length == 0) {
                $(value).parent().addClass("error");

            } else {
                $(value).parent().removeClass("error");

            }
        });

        var errorInput = $(".createCustomer-form .form_input.error");
        if (errorInput.length > 0) {
            $(".createCustomer-form .errorMsg").show();
            $(".createCustomer-form .errorMsg").html("Please fill in all the required fields (highlighted in red)");
            isFormValid = false;
        } else {
            $(".createCustomer-form .errorMsg").hide();
            $(".createCustomer-form .errorMsg").html("");
            isFormValid = true;
        }

        if (isFormValid) {
            var formData = {}
            $('#createNewCustomerModel .form_input input').each(function() {
                formData[$(this).attr('name')] = $(this).val();
            });
            $.ajax({
                type: "POST",
                url: "/v1/deployer/customers/",
                async: false,
                dataType: 'json',
                data: JSON.stringify(formData),
                success: function(data) {
                    if (data.response == 200) {
                        $('#createNewCustomerModel').modal();
                        $("#createNewCustomerModel .modal-body .form_fields_container").hide();
                        $("#createNewCustomerModel .modal-body .sucessMsg").show();
                        $(".createNewCustomerBtn").hide();
                        $("#createNewCustomerModel .cancelButton").show();
                        $("#createNewCustomerModel .modal-body .sucessMsg").html(data.message);
                        getCustomers();

                        $('.createCustomer-form').find('input').val('');
                        //$('.createCustomer-form').find('input:email').val('');
                        location.reload(false);
                    } else {
                        $('#createNewCustomerModel').modal();
                        $("#createNewCustomerModel .modal-body .form_fields_container").hide();
                        $("#createNewCustomerModel .modal-body .sucessMsg").show();
                        $(".createNewCustomerBtn").hide();
                        $("#createNewCustomerModel .cancelButton").show();
                        $("#createNewCustomerModel .modal-body .sucessMsg").html(data.error);
                        //location.reload(false);
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $('#createNewCustomerModel').modal();
                    $("#createNewCustomerModel .modal-body").html("Unable to Create New Customer.");
                }
            });
        }
    });


     $(".customersDetailsTable tbody").on('click', 'tr', function() {
        $(".customersDetailsTable tbody tr").removeClass("row_selected");
        $(this).addClass("row_selected");
        var customerId = $(this).find('td.customerId').html();
        if($(this).find("td.task").text() == "Deployment" ){ 
            $("a.kickoffBtn").show();
        }else{
            $("a.kickoffBtn").hide();
        }
    });
    
    
    $("a.kickoffBtn").click(function() {
        var cutomerId = $(".customersTable tr.row_selected td.customerId").text();
        var taskId =  $(".customersDetailsTable  tr.row_selected td.id").text();
        prevCustomerTask(cutomerId,taskId);
    });

    function prevCustomerTask(cutomerId,taskId) {
        var json_data = {"customer_id":cutomerId,"task_id":taskId}
        $.ajax({
            type: "POST",
            url: "/prevTask/",
            async: false,
            dataType: "json",
            data: JSON.stringify(json_data),
            success: function(data) {
                $( "#mainTabContainer" ).tabs("enable", 1).tabs("select", 1);
                importData(data.json_form);
            },
            error: function(request, status, errorThrown) {
                alert("No Data Available");
            }
        });
    }

    function defaultTabSelection(){
        $("#preDeploy_secondaryNav ul li").removeClass("active").addClass("disabled");
        $("#preDeploy_secondaryNav ul li:first-child").removeClass("disabled").addClass("active");
        var tab = $("#preDeploy_secondaryNav ul li:first-child a").attr("href");
        $(".tab-content").not(tab).css("display", "none");
        $(tab).fadeIn();
    }
    
    function createCustomerTask(cutomerId, json_data) {
        defaultTabSelection();
        $.ajax({
            type: "POST",
            url: "/v1/deployer/customers/" + cutomerId + "/tasks/",
            async: false,
            dataType: "json",
            data: JSON.stringify(json_data),
            success: function(data) {
                if (data.response == 200) {
                    $("#task_id").val(data.task_id);
                    $(".successMessage").show();
                    $("#mainTabContainer").tabs("enable", 2).tabs("select", 2);
                    $(".preDeploy_maincontent input[type=text]").val("");
                } else {
                    $('#commonModal').modal();
                    $("#commonModal .modal-body").html("Unable to create task.");
                }
            },
            error: function(request, status, errorThrown) {
                alert("No Data Available");
            }
        });
    }

    /*Import Predeployer Data Start*/
    if (window.File && window.FileList && window.FileReader) {
        var filesInput =  document.getElementById("importjsonFile");
        filesInput.addEventListener("change", function(event) {
            var files = event.target.files; //FileList object
            var output = document.getElementById("result");
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                var picReader = new FileReader();

                picReader.addEventListener("load", function(event) {
                    var textFile = event.target;
                    var parsefile = JSON.parse(textFile.result);	
                    importData(parsefile);
                });
                //Read the text file
                picReader.readAsBinaryString(file);
            }

        });
    }
    else {
        console.log("Your browser does not support File API");
    }
    
    
    function importData(fileData){
        defaultTabSelection();
        /*Cluster Configuration values*/
        $('#cluster_name').val(fileData.foundation.restInput.clusters[0].cluster_name);
        $('#externalIP').val(fileData.foundation.restInput.clusters[0].cluster_external_ip);
        $('#redundancy_factor').val("null");
        $('#hypervisor').val(fileData.foundation.restInput.hypervisor);
        if(fileData.foundation.restInput.hyperv_sku == null){
            $('#hyperv_sku').val("null");
        }else{
            $('#hyperv_sku').val(fileData.foundation.restInput.hyperv_sku);
        }
        $('#node_ram').val(fileData.foundation.restInput.blocks[0].nodes[0].cvm_gb_ram);
        
        var blocksLenght = fileData.foundation.restInput.blocks.length;
        var i,nodeLenght;
        for(i=0;i<blocksLenght;i++){
            nodeLenght = fileData.foundation.restInput.blocks[i].nodes.length;
            for(j=0;j<nodeLenght;j++){
                $("#block-"+(i+1)+" #node-"+(j+1)+" #ipmimac").val(fileData.foundation.restInput.blocks[i].nodes[j].ipmi_mac);
                $("#block-"+(i+1)+" #node-"+(j+1)+" #ipmiip").val(fileData.foundation.restInput.blocks[i].nodes[j].ipmi_ip);
                $("#block-"+(i+1)+" #node-"+(j+1)+" #hyperversionhostname").val(fileData.foundation.restInput.blocks[i].nodes[j].hypervisor_hostname);
                $("#block-"+(i+1)+" #node-"+(j+1)+" #hyperversionip").val(fileData.foundation.restInput.blocks[i].nodes[j].hypervisor_ip);
                $("#block-"+(i+1)+" #node-"+(j+1)+" #cvmip").val(fileData.foundation.restInput.blocks[i].nodes[j].cvm_ip);
                $("#block-"+(i+1)+" #node-"+(j+1)+" #ipv6_address").val(fileData.foundation.restInput.blocks[i].nodes[j].ipv6_address);
            }
        }
        
        /*Networking  values*/
        $('#IPMGateway').val(fileData.foundation.restInput.ipmi_gateway);
        $('#IPNM').val(fileData.foundation.restInput.ipmi_netmask);
        $('#HyperversionGateway').val(fileData.foundation.restInput.hypervisor_gateway);
        $('#HyperversionNM').val(fileData.foundation.restInput.hypervisor_netmask);
        $('#HYPERVERSIONCVMNTPSERVER').val(fileData.foundation.restInput.clusters[0].hypervisor_ntp_servers);
        $('#HyperverNameServer').val(fileData.foundation.restInput.hypervisor_nameserver);
        $('#Cvmgateway').val(fileData.foundation.restInput.cvm_gateway);
        $('#CvmNM').val(fileData.foundation.restInput.cvm_netmask);
        $('#CVMNTPSERVER').val(fileData.foundation.restInput.clusters[0].cvm_ntp_servers);
        $('#CVMDNSSERVER').val(fileData.foundation.restInput.clusters[0].cvm_dns_servers);        
        
        
        /*Credentials values*/
        $('#IPMIUsernanme').val(fileData.foundation.restInput.ipmi_user);
        $('#IPMIPass').val(fileData.foundation.restInput.ipmi_password);
        $('#pusername').val(fileData.prismDetails.authentication.username);
        $('#ppassword').val(fileData.prismDetails.authentication.password);
        $('#v_center_user').val(fileData.vCenterConf.user);
        $('#v_center_password').val(fileData.vCenterConf.password);
        //$('#hypervisorpass').val(fileData.foundation.restInput.);
        
        /*Storage values*/
        $('#storagepool_name').val(fileData.prismDetails.storagepool.name);
        $('#container_name').val(fileData.prismDetails.container.name);
        
        /*vCenter values*/
        $('#v_center_host').val(fileData.vCenterConf.host);
        $('#vcenter_port').val(fileData.vCenterConf.port);
        $('#v_center_user').val(fileData.vCenterConf.user);
        $('#v_center_vm_password').val(fileData.vCenterConf.hosts[0].pwd);
        $('#v_center_datacenter').val(fileData.vCenterConf.datacenter);
        $('#v_center_datacenter_reuse').val(fileData.vCenterConf.datacenter_reuse_if_exist);
        $('#v_center_cluster').val(fileData.vCenterConf.cluster);
        $('#v_center_cluster_reuse').val(fileData.vCenterConf.cluster_reuse_if_exist);
        
        /*Deployer Infrastructure values*/
        $("#foundation_server_ip").val(fileData.foundation.server);
    }
    /*Import Predeployer Data Start*/
    
    /*Predeployer Submit Start*/

    var main_rest_block = {};
    $("#submit_all").click(function() {
        var isFormValid = true;
        var currentContainer = $(this).parents().eq(1).find(".mainBody_container input.required");
        currentContainer.each(function(index, value) {
            if ($.trim($(value).val()).length == 0) {
                $(value).addClass("error");
            } else {
                $(value).removeClass("error");
            }
        });
        var errorInput = $(this).parents().eq(1).find(".mainBody_container input.error");
        if (errorInput.length > 0) {
            $(this).parents().eq(1).find(".errorMsg").show();
            $(this).parents().eq(1).find(".errorMsg").html("Please fill in all the required fields (highlighted in red)");
            isFormValid = false;
        } else {
            $(this).parents().eq(1).find(".errorMsg").hide();
            $(this).parents().eq(1).find(".errorMsg").html("");
            isFormValid = true;
        }

        if (isFormValid) {
            var mainObject = {};
            var foundationObject = {};
            var restInput = {};

            foundationObject["ipmi_netmask"] = $('#IPNM').val();
            foundationObject["ipmi_gateway"] = $('#IPMGateway').val();
            foundationObject["ipmi_user"] = $('#IPMIUsernanme').val();
            foundationObject["ipmi_password"] = $('#IPMIPass').val();

            foundationObject["hypervisor_netmask"] = $('#HyperversionNM').val();
            foundationObject["hypervisor_gateway"] = $('#HyperversionGateway').val();
            foundationObject["hypervisor_nameserver"] = $('#HyperverNameServer').val();

            foundationObject["cvm_netmask"] = $('#CvmNM').val();
            foundationObject["cvm_gateway"] = $('#Cvmgateway').val();
            //foundationObject["cvmmemory"] = $('#CvmMemory').val()

            //        foundationObject["cluster_name"] = $('#cluster_name').val();
            //        foundationObject["cluster_external_ip"] = $.trim($('#externalIP').val());
            /*
            var redundancy_factor = $('#redundancy_factor').val();
            if (redundancy_factor == "null") {
                redundancy_factor = null;
            }
            foundationObject["redundancy_factor"] = redundancy_factor;
            */
            //        foundationObject["cvm_dns_servers"] = $('#CVMDNSSERVER').val();
            //        foundationObject["cvm_ntp_servers"] = $('#CVMNTPSERVER').val();
            //        foundationObject["hypervisor_ntp_servers"] = $('#HYPERVERSIONCVMNTPSERVER').val();

            foundationObject["phoenix_iso"] = $('#phoenix_iso').val();
            foundationObject["hypervisor_iso"] = $('#hypervisor_iso').val();

            if ($("input[name=foundation_ip]:checked").val() == "true"){
                foundationObject['use_foundation_ips'] = true; 
            }
            else{
                foundationObject['use_foundation_ips'] = false;
            }
            
            //foundationObject["cluster_init_successful"] = null;
            //foundationObject['hypervisor_password'] = $('#hypervisorpass').val();

            foundationObject["hypervisor_iso"] = $('#hypervisor_iso').val();

            foundationObject["hypervisor"] = $('#hypervisor').val();
            
            if (foundationObject["hyperv_sku"] = "null"){
                foundationObject["hyperv_sku"] = null
            }
            else{
                foundationObject["hyperv_sku"] = $('#hyperv_sku').val();
            }
            
            foundationObject["phoenix_iso"] = $('#phonix_iso').val();
            
            if ($("input[name=skip_hypervisor]:checked").val() == "true"){
                foundationObject['skip_hypervisor'] = true; 
            }
            else{
                foundationObject['skip_hypervisor'] = false;
            }

            var nodes = [];
            var mainblock = {}
            var blocks = [];
            var clusters = [];
            var tests = {};
            var hosts = [];
            var clusterMembersArray = [];

            foundationObject["ipmi_netmask"] = $('#IPNM').val();

            var blocklength = $(".blockContainer").length;
            $('div.blockContainer').each(function() {
                var block_id = $(this).attr("id");
                var nodelength = $("#" + block_id + " .nodeContainer").length;
                var i = 1;
                var j = 1;
                $("#" + block_id + " .nodeContainer").each(function() {
                    var node_id = $(this).attr("id");
                    var vcenterhosts = {};
                    var a = $("#" + block_id + " #" + node_id + " #ipmimac").val();
                    var nodeObject = {};
                    nodeObject['ipmi_mac'] = $("#" + block_id + " #" + node_id + " #ipmimac").val();
                    nodeObject['ipmi_ip'] = $("#" + block_id + " #" + node_id + " #ipmiip").val();
                    nodeObject['hypervisor_ip'] = $("#" + block_id + " #" + node_id + " #hyperversionip").val();

                    nodeObject['cvm_ip'] = $("#" + block_id + " #" + node_id + " #cvmip").val();
                    clusterMembersArray.push($("#" + block_id + " #" + node_id + " #cvmip").val());

                    if (j == 1 || j == "1") {

                        var restbaseurl = "https://" + nodeObject['cvm_ip'] + ":9440/PrismGateway/services/rest/";
                        $('#restURL').val(restbaseurl);
                    }

                    nodeObject['hypervisor_hostname'] = $("#" + block_id + " #" + node_id + " #hyperversionhostname").val();

                    vcenterhosts['ip'] = $("#" + block_id + " #" + node_id + " #hyperversionip").val();
                    vcenterhosts['user'] = $('#v_center_user').val();
                    vcenterhosts['pwd'] = $('#v_center_vm_password').val();
                    hosts.push(vcenterhosts);

                    nodeObject['cvm_gb_ram'] = parseInt($('#node_ram').val());
                    nodeObject['ipv6_address'] = $("#" + block_id + " #" + node_id + " #ipv6_address").val();
                    nodeObject['ipmi_configure_successful'] = true;
                    if ($("#" + block_id + " #" + node_id + " input[name=ipmi_configure_now-" + node_id + "]:checked").val() == "true"){
                        nodeObject['ipmi_configure_now']  = true;
                    }
                    else{
                        nodeObject['ipmi_configure_now'] = false;
                    }

                    nodeObject['ipv6_interface'] = "";
                    nodeObject['node_position'] = $("#" + block_id + " #" + node_id + " #nodePosition").val();
                    
                    if($("#" + block_id + " #" + node_id + " input[name=image_now-" + node_id + "]:checked").val() == "true"){
                        nodeObject['image_now'] = true;
                    }
                    else{
                        nodeObject['image_now'] = false;
                    }
                    var image_successful = $("#" + block_id + " #" + node_id + " #image_successful").val();
                    if (image_successful == "") {
                        nodeObject['image_successful'] = false;
                    } else {
                        nodeObject['image_successful'] = image_successful;
                    }
                    //nodeObject['ipmi_configured'] = $("#" + block_id + " #" + node_id + " input[name=ipmi_configured-" + node_id + "]:checked").val();

                    nodes.push(nodeObject);
                    j = j + 1;
                })

                mainblock['nodes'] = nodes;
                mainblock['model'] = "undefined";
                mainblock['ui_block_id'] = "Block-" + i;
                mainblock['block_id'] = "null";
                i = i + 1;
            });
            blocks.push(mainblock);
            foundationObject['blocks'] = blocks;

            var clusterObjects = {};
            clusterObjects['cluster_external_ip'] = $.trim($('#externalIP').val());
            clusterObjects['cluster_init_successful'] = false;
            clusterObjects['log_id'] = 3;
            clusterObjects['cluster_name'] = $('#cluster_name').val();
            clusterObjects['cvm_ntp_servers'] = $('#CVMNTPSERVER').val();
            clusterObjects['cvm_dns_servers'] = $('#CVMDNSSERVER').val();
            clusterObjects['cluster_init_now'] = true;
            clusterObjects['hypervisor_ntp_servers'] = $('#HYPERVERSIONCVMNTPSERVER').val();
            clusterObjects['cluster_members'] = clusterMembersArray;

            clusters.push(clusterObjects);

            foundationObject['clusters'] = clusters;

            /*
            tests['run_diagnostics'] = $("input[name=run_diagnostics]:checked").val();
            tests['run_ncc'] = $("input[name=run_ncc]:checked").val();
            */
            if ($("input[name=run_diagnostics]:checked").val() == "true"){
                tests['run_diagnostics'] = true; 
            }
            else{
                tests['run_diagnostics'] = false;
            }
            if ($("input[name=run_ncc]:checked").val() == "true"){
                tests['run_ncc'] = true; 
            }
            else{
                tests['run_ncc'] = false;
            }
            foundationObject['tests'] = tests;

            restInput['restInput'] = foundationObject;
            restInput['server'] = $('#foundation_server_ip').val();
            main_rest_block['foundation'] = restInput;

            var prismObject = {};
            var authentication = {};
            var container = {};
            var storagepool = {};

            prismObject['restURL'] = $('#restURL').val();
            authentication['username'] = $('#pusername').val();
            authentication['password'] = $('#ppassword').val();
            prismObject['authentication'] = authentication;

            container['name'] = $('#container_name').val();
            prismObject['container'] = container;

            storagepool['name'] = $('#storagepool_name').val();
            prismObject['storagepool'] = storagepool;
            main_rest_block['prismDetails'] = prismObject;

            var vCenterObject = {};

            vCenterObject['host'] = $('#v_center_host').val();
            vCenterObject['user'] = $('#v_center_user').val();
            vCenterObject['password'] = $('#v_center_password').val();
            vCenterObject['port'] = $('#vcenter_port').val();

            vCenterObject['datacenter'] = $('#v_center_datacenter').val();
            vCenterObject['cluster'] = $('#v_center_cluster').val();
            vCenterObject['datacenter_reuse_if_exist'] = $('#v_center_datacenter_reuse').val();
            vCenterObject['cluster_reuse_if_exist'] = $('#v_center_cluster_reuse').val();

            vCenterObject['hosts'] = hosts;
            main_rest_block['vCenterConf'] = vCenterObject;

            var customerId = $("#customerId").val();
            createCustomerTask(customerId, main_rest_block);
        }
    });

    /*Predeployer Submit Ends*/


    $(".startDeploymentBtn").click(function() {
        $(".pageloader").show();
        var customerId = $("#customerId").val();
        var taskId = $("#task_id").val();

        var checkValues = [];
        checked = $('input[name=deployment_type]:checked');
        if (checked.length > 0) {
            checkValues = checked.map(function() {
                return $(this).val();
            }).get();
        }

        startDeployment(customerId, taskId, checkValues);
    });

    var interval = null;
    var completeTask = false;

    var prismCheck = false;
    var vcenterCheck = false;

    function startDeployment(customerId, taskId, checkValues) {
        var post_data = {};
        post_data["customer_id"] = customerId;
        post_data["task_id"] = taskId;
        post_data["module_id"] = "foundation";



        if (checkValues.indexOf("foundation") > -1) {
            console.log(JSON.stringify(checkValues));

            $.ajax({
                type: "POST",
                url: "/v1/deployer/action/",
                async: false,
                dataType: "json",
                data: JSON.stringify(post_data),
                success: function(data) {
                    //alert(data);
                },
                error: function(request, status, errorThrown) {
                    alert("No Data Available");
                }
            });


            $(".pageloader").fadeOut("slow");
            deployementStatus(customerId, taskId, checkValues);
            interval = setInterval(function() {
                deployementStatus(customerId, taskId, checkValues); // this will run after every 10 seconds
            }, 10000);

        }


        if (checkValues.indexOf("vcenter") > -1 && checkValues.indexOf("foundation") == -1) {
            post_data["module_id"] = "vcenter";
            $.ajax({
                type: "POST",
                url: "/v1/deployer/action/",
                async: false,
                dataType: "json",
                data: JSON.stringify(post_data),
                success: function(data) {
                    //alert(data);
                    vcenterCheck = true;
                },
                error: function(request, status, errorThrown) {
                    alert("No Data Available");
                }
            });
            $(".pageloader").fadeOut("slow");
            deployementStatus(customerId, taskId, checkValues);
        }
    }

    function deployementStatus(customerId, taskId, checkValues) {
        $.ajax({
            type: "GET",
            url: "/v1/deployer/customers/" + customerId + "/tasks/" + taskId + "/status/",
            async: false,
            dataType: "json",
            success: function(data) {
                for (var i = 0; i < data.task_status.length; i++) {
                    if (data.task_status[i].module == "foundation") {
                        $("#foundationStatus .progressPercentage").html(data.task_status[i].status);
                        if (data.task_status[i].status == "100.0%") {
                            if (checkValues.indexOf("prism") > -1) {
                                var post_data = {};
                                post_data["customer_id"] = customerId;
                                post_data["task_id"] = taskId;
                                post_data["module_id"] = "prism";
                                $.ajax({
                                    type: "POST",
                                    url: "/v1/deployer/action/",
                                    async: false,
                                    dataType: "json",
                                    data: JSON.stringify(post_data),
                                    success: function(data) {
                                        //alert(data);
                                        completeTask = true;
                                        prismCheck = true;
                                    },
                                    error: function(request, status, errorThrown) {
                                        alert("No Data Available");
                                    }
                                });

                            }
                            if (checkValues.indexOf("vcenter") > -1) {
                                var post_data = {};
                                post_data["customer_id"] = customerId;
                                post_data["task_id"] = taskId;
                                post_data["module_id"] = "vcenter";
                                $.ajax({
                                    type: "POST",
                                    url: "/v1/deployer/action/",
                                    async: false,
                                    dataType: "json",
                                    data: JSON.stringify(post_data),
                                    success: function(data) {
                                        //alert(data);
                                        completeTask = true;
                                        vcenterCheck = true;
                                    },
                                    error: function(request, status, errorThrown) {
                                        alert("No Data Available");
                                    }
                                });

                            }


                            $("#foundationStatus .status").removeClass("progressActiveSec").addClass("taskCompleted").append("<i class='fa fa-check-square'></i>");
                            $("#foundationStatus .statusMessage").html("Setup Completed...");
                        } else {
                            $("#foundationStatus .status").html("");
                            $("#foundationStatus .status").removeClass("taskCompleted").addClass("progressActiveSec");
                            $("#foundationStatus .statusMessage").html("Setup InProgress...");
                        }
                    }
                    if (data.task_status[i].module == "prism" && prismCheck && completeTask) {
                        $("#prismStatus .progressPercentage").html(data.task_status[i].status);
                        if (data.task_status[i].status == "Failed") {
                            $("#prismStatus .status").html("");
                            $("#prismStatus .status").removeClass("progressActiveSec").addClass("taskError").append("<i class='fa fa-exclamation-triangle'></i>");
                            $("#prismStatus .statusMessage").html("Setup Failed...");
                        } else if (data.task_status[i].status == "Completed") {
                            $("#prismStatus .status").html("");
                            $("#prismStatus .status").removeClass("progressActiveSec").addClass("taskCompleted").append("<i class='fa fa-check-square'></i>");
                            $("#prismStatus .statusMessage").html("Setup Completed...");
                        } else {
                            $("#prismStatus .status").html("");
                            $("#prismStatus .status").addClass("progressActiveSec");
                            $("#prismStatus .statusMessage").html("Setup InProgress...");
                        }
                    }

                    if (data.task_status[i].module == "vcenter" && vcenterCheck && completeTask) {
                        $("#vcenterStatus .progressPercentage").html(data.task_status[i].status);
                        if (data.task_status[i].status == "Failed") {
                            $("#vcenterStatus .status").html("");
                            $("#vcenterStatus .status").removeClass("progressActiveSec").addClass("taskError").append("<i class='fa fa-exclamation-triangle'></i>");
                            $("#vcenterStatus .statusMessage").html("Setup Failed...");
                        } else if (data.task_status[i].status == "Completed") {

                            $("#vcenterStatus .status").removeClass("progressActiveSec").addClass("taskCompleted").append("<i class='fa fa-check-square'></i>");
                            $("#vcenterStatus .statusMessage").html("Setup Completed...");
                        } else {
                            $("#vcenterStatus .status").html("");
                            $("#vcenterStatus .status").addClass("progressActiveSec");
                            $("#vcenterStatus .statusMessage").html("Setup InProgress...");
                        }
                    }
                }
            },
            error: function(request, status, errorThrown) {
                alert("No Data Available");
            }
        });
    }


    /*post deploye / health check run*/
    $(".runCheck").click(function() {
        var categoryType = $(this).attr("name");
        function fetch_data() {
            $.ajax({
                url: '/refresh',
                type: "GET",
                dataType: "json",
                success: function(data) {
                    if (categoryType == "ncc") {
                        $("#logs").empty();
                        $("#logs").append("<div id='nccDataHead' class='logsHeading col-lg-12 col-md-12 col-sm-12'>" +
                            "<div class='col-lg-10 col-md-10 col-sm-10'><span>Check</span></div>" +
                            "<div class='col-lg-2 col-md-2 col-sm-2'><span>Status</span></div>" +
                            "</div>");
                        $("#logs").append("<div id='nccMainData' class='logsdata col-lg-12 col-md-12 col-sm-12'></div>");
                        for (i = 0; i < data.ncc.checks.length; i++) {
                            $("#logs .logsdata").append("<div class='logsmainData'><div class='col-lg-10 col-md-10 col-sm-10'><span>" + data.ncc.checks[i].Name + "</span></div>" +
                                "<div class='col-lg-2 col-md-2 col-sm-2 result" + i + "'><span>" + data.ncc.checks[i].Status + "</span></div></div>");
                            if (($(".result" + i + " span").html()).toLowerCase() == "pass") {
                                $(".result" + i + " span").addClass("success");
                            } else if (($(".result" + i + " span").html()).toLowerCase() == "fail") {
                                $(".result" + i + " span").addClass("fail");
                            }
                            var h1 = $('#logs')[0].scrollHeight,
                                h2 = $('#logs').height();
                            $('#logs').scrollTop(h1 - h2);
                        }

                    }
                    if (categoryType == "view") {
                        $("#logs").empty();
                        $("#nccDataHead").remove();
                        $("#nccMainData").remove();
                        $("#logs").empty();
                        $("#vcMainData").remove();
                        $("#vcDataHead").remove();
                        for (i = 0; i < data.view.checks.length; i++) {
                            $("#logs").append("<h4>" + data.view.checks[i].Message + "</h4>");
                            $("#logs").append("<div class='logsHeading col-lg-12 col-md-12 col-sm-12'>" +
                                "<div class='col-lg-5 col-md-5 col-sm-5'><span>Actual</span></div>" +
                                "<div class='col-lg-5 col-md-5 col-sm-5'><span>Expected</span></div>" +
                                "<div class='col-lg-2 col-md-2 col-sm-2'><span>Status</span></div>" +
                                "</div>");
                            $("#logs").append("<div class='logsdata" + i + " col-lg-12 col-md-12 col-sm-12 logsdata'></div>");
                            for (j = 0; j < data.view.checks[i].Properties.length; j++) {
                                $("#logs .logsdata" + i).append("<div class='logsmainData'><div class='col-lg-5 col-md-5 col-sm-5'><span>" + data.view.checks[i].Properties[j].Actual.replace(/;/g, '<BR/>') + "</span></div>" +
                                    "<div class='col-lg-5 col-md-5 col-sm-5'><span>" + data.view.checks[i].Properties[j].Expected.replace(/;/g, '<br/>') + "</span></div>" +
                                    "<div class='col-lg-2 col-md-2 col-sm-2  result" + i + j + "'><span>" + data.view.checks[i].Properties[j].Status + "</span></div></div>");

                                if (($(".result" + i + j + " span").html()).toLowerCase() == "pass") {
                                    $(".result" + i + j + " span").addClass("success");
                                } else if (($(".result" + i + j + " span").html()).toLowerCase() == "fail") {
                                    $(".result" + i + j + " span").addClass("fail");
                                }
                            }
                        }
                        var h1 = $('#logs')[0].scrollHeight,
                            h2 = $('#logs').height();
                        $('#logs').scrollTop(h1 - h2);

                    }
                    if (categoryType == "vc") {
                        $("#logs").empty();
                        $("#nccDataHead").remove();
                        $("#nccMainData").remove();
                        $("#logs").empty();
                        $("#viewMainData").remove();
                        $("#viewDataHead").remove();
                        for (i = 0; i < data.vc.checks.length; i++) {
                            $("#logs").append("<h4>" + data.vc.checks[i].Message + "</h4>");
                            $("#logs").append("<div class='logsHeading col-lg-12 col-md-12 col-sm-12'>" +
                                "<div class='col-lg-7 col-md-7 col-sm-7'><span>Check</span></div>" +
                                "<div class='col-lg-2 col-md-2 col-sm-2'><span>Expected</span></div>" +
                                "<div class='col-lg-2 col-md-2 col-sm-2'><span>Actual</span></div>" +
                                "<div class='col-lg-1 col-md-1 col-sm-1'><span>Status</span></div>" +
                                "</div>");
                            $("#logs").append("<div class='logsdata" + i + " col-lg-12 col-md-12 col-sm-12 logsdata'></div>");
                            for (j = 0; j < data.vc.checks[i].Properties.length; j++) {
                                $("#logs .logsdata" + i).append("<div class='logsmainData'><div class='col-lg-7 col-md-7 col-sm-7'><span>" + data.vc.checks[i].Properties[j].Message + "</div>" +
                                    "<div class='col-lg-2 col-md-2 col-sm-2'><span>" + data.vc.checks[i].Properties[j].Expected + "</span></div>" +
                                    "<div class='col-lg-2 col-md-2 col-sm-2'><span>" + data.vc.checks[i].Properties[j].Actual + "</span></div>" +
                                    "<div class='col-lg-1 col-md-1 col-sm-1  result" + i + j + "'><span>" + data.vc.checks[i].Properties[j].Status + "</span></div></div>");

                                if (($(".result" + i + j + " span").html()).toLowerCase() == "pass") {
                                    $(".result" + i + j + " span").addClass("success");
                                } else if (($(".result" + i + j + " span").html()).toLowerCase() == "fail") {
                                    $(".result" + i + j + " span").addClass("fail");
                                }
                            }
                        }
                        var h1 = $('#logs')[0].scrollHeight,
                            h2 = $('#logs').height();
                        $('#logs').scrollTop(h1 - h2);
                    }
                    $("#failCheck").val(data.FAIL);
                    $("#passCheck").val(data.PASS);
                    $("#totalCheck").val(data.Total);
                    $("#totalPercentage").val(data.Percent);
                },
                beforeSend: function() {

                    $("." + categoryType + "Status .progressPercentage").html("");
                    $("." + categoryType + "Status .status").html("");
                    $("." + categoryType + "Status .status").removeClass("taskCompleted").addClass("progressActiveSec");
                    $("." + categoryType + "Status .statusMessage").html("Running " + $('#' + categoryType + '_types :selected').text() + "...");
                    $(".hc_types .runCheck").attr("disabled", "disabled");
                    $(".hc_types select").attr("disabled", "disabled");

                }
            });
        }

        checks = [];
        var group = $("#" + categoryType + "_types").val();
        $("#logs").empty();
        checks.push({
            name: "category",
            value: categoryType
        });
        checks.push({
            name: "group",
            value: group
        });
        checks.push({
            name: "customerId",
            value: $("#customerId").val()
        });


        console.log(checks)
        $.ajax({
            url: '/run',
            type: "POST",
            data: checks,
            dataType: 'html',
            success: function(data) {
                looping = false;
                fetch_data();
                clearInterval(interval);
                setTimeout(function() {
                    $("#modal_runchecks .runckeckStatus").html(data);
                    $("#modal_runchecks").modal();
                    $("." + categoryType + "Status .progressPercentage").html("");
                    $("." + categoryType + "Status .progressPercentage").append("<p><span class='checkText'>Total Checks:</span><span class='checkValue'>" + $('#totalCheck').val() + "</span></p>" +
                        "<p><span class='checkText'>Total Pass:</span><span class='checkValue'>" + $('#passCheck').val() + "</span></p>" +
                        "<p><span class='checkText'>Total Fail:</span><span class='checkValue'>" + $('#failCheck').val() + "</span></p>" +
                        "<p><span class='checkText'>Total Percentage:</span><span class='checkValue'>" + $('#totalPercentage').val() + "%</span></p>");
                    $("." + categoryType + "Status .status").html("");
                    $("." + categoryType + "Status .status").removeClass("progressActiveSec").addClass("taskCompleted").append("<i class='fa fa-check-square'></i>");
                    $("." + categoryType + "Status .statusMessage").html($('#' + categoryType + '_types :selected').text() + " Completed...");
                    $(".hc_types .runCheck").removeAttr("disabled");
                    $(".hc_types select").removeAttr("disabled");

                }, 2000);
            },
        });
        var interval = setInterval(function() {
            fetch_data()
        }, 3000);
        return false;
    });


    $(".conf").click(function() {
        if ($(this).attr('id') == "config_vc") {
            var form_data = $("#vc").serializeArray();
            form_data.push({
                name: 'checker',
                value: 'vc'
            });
            console.log(form_data)
            $.ajax({
                url: '/config',
                type: "POST",
                //contentType: 'application/json',		                
                dataType: "json",
                data: form_data,
                success: function(value) {
                    console.log(value)
                        //alert("Successfully Updated")
                    $("#healthCheckConfigurationModel .statusmessage").show();
                    $("#healthCheckConfigurationModel .statusmessage").html("Successfully Updated");
                    $(".modal-content#modal_vc .formTbl").hide();
                    $(".modal-content#modal_ncc .formTbl").hide();
                    $(".modal-content#modal_view .formTbl").hide();
                    $("#healthCheckConfigurationModel .cancelButton").show();
                    $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").hide();
                },
            });
        }
        if ($(this).attr('id') == "config_ncc") {

            var form_data = $("#ncc").serializeArray();
            form_data.push({
                name: 'checker',
                value: 'ncc'
            });
            $.ajax({
                url: '/config',
                type: "POST",
                //contentType: 'application/json',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    //alert("Successfully Updated");
                    $("#healthCheckConfigurationModel .statusmessage").show();
                    $("#healthCheckConfigurationModel .statusmessage").html("Successfully Updated");
                    $(".modal-content#modal_vc .formTbl").hide();
                    $(".modal-content#modal_ncc .formTbl").hide();
                    $(".modal-content#modal_view .formTbl").hide();
                    $("#healthCheckConfigurationModel .cancelButton").show();
                    $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").hide();
                },
            });
        }
        if ($(this).attr('id') == "config_view") {
            var form_data = $("#view").serializeArray();
            form_data.push({
                name: 'checker',
                value: 'view'
            });
            console.log(form_data)
            $.ajax({
                url: '/config',
                type: "POST",
                dataType: "json",
                data: form_data,
                success: function(value) {
                    console.log(value)
                        //alert("Successfully Updated")
                    $("#healthCheckConfigurationModel .statusmessage").show();
                    $("#healthCheckConfigurationModel .statusmessage").html("Successfully Updated");
                    $(".modal-content#modal_vc .formTbl").hide();
                    $(".modal-content#modal_ncc .formTbl").hide();
                    $(".modal-content#modal_view .formTbl").hide();
                    $("#healthCheckConfigurationModel .cancelButton").show();
                    $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").hide();
                },
            });
        }
        return false;
    });

    $(".conn").click(function() {
        if ($(this).attr('id') == "connect_vc") {
            var form_data = $("#vc").serializeArray();
            form_data.push({
                name: 'checker',
                value: 'vc'
            });

            $.ajax({
                url: '/connect',
                type: "POST",
                //contentType: 'application/x-www-form-urlencoded',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    console.log(data)
                    var status = data["Connection"];
                    console.log(status);
                    $("#healthCheckConfigurationModel .statusmessage").show();
                    $("#healthCheckConfigurationModel .statusmessage").html(status);
                    $(".modal-content#modal_vc .formTbl").hide();
                    $(".modal-content#modal_ncc .formTbl").hide();
                    $(".modal-content#modal_view .formTbl").hide();
                    $("#healthCheckConfigurationModel .cancelButton").show();
                    $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").hide();
                },
            });
        }
        if ($(this).attr('id') == "connect_ncc") {
            var form_data = $("#ncc").serializeArray();
            form_data.push({
                name: 'checker',
                value: 'ncc'
            });

            $.ajax({
                url: '/connect',
                type: "POST",
                //contentType: 'application/x-www-form-urlencoded',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    console.log(data)
                    var status = data["Connection"];
                    console.log(status);
                    $("#healthCheckConfigurationModel .statusmessage").show();
                    $("#healthCheckConfigurationModel .statusmessage").html(status);
                    $(".modal-content#modal_vc .formTbl").hide();
                    $(".modal-content#modal_ncc .formTbl").hide();
                    $(".modal-content#modal_view .formTbl").hide();
                    $("#healthCheckConfigurationModel .cancelButton").show();
                    $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").hide();
                },
            });
        }
        if ($(this).attr('id') == "connect_view") {
            var form_data = $("#view").serializeArray();
            form_data.push({
                name: 'checker',
                value: 'view'
            });

            $.ajax({
                url: '/connect',
                type: "POST",
                //contentType: 'application/x-www-form-urlencoded',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    console.log(data)
                    var status = data["Connection"];
                    console.log(status);
                    $("#healthCheckConfigurationModel .statusmessage").show();
                    $("#healthCheckConfigurationModel .statusmessage").html(status);
                    $(".modal-content#modal_vc .formTbl").hide();
                    $(".modal-content#modal_ncc .formTbl").hide();
                    $(".modal-content#modal_view .formTbl").hide();
                    $("#healthCheckConfigurationModel .cancelButton").show();
                    $("#healthCheckConfigurationModel .conf, #healthCheckConfigurationModel .conn").hide();
                },
            });
        }
        return false;
    });

    var machineCheck = $("#machineCheck").val();
    if(machineCheck == "windows"){
    	$(".vmwarecheck .hc_types .runCheck").removeAttr("disabled");
        $(".vmwarecheck .hc_types select").removeAttr("disabled");
        $(".viewStatus 	.progressStatusMessage").show();
        $(".viewStatus 	.errorSupport").hide();
        $(".viewStatus 	.errorSupport .errorMessage").html("");
        $(".vmwarecheck .hc_types.viewtype .editCheck").removeAttr("disabled");
    }else{
    	$(".vmwarecheck .hc_types .runCheck").attr("disabled", "disabled");
        $(".vmwarecheck .hc_types select").attr("disabled", "disabled");
        $(".vmwarecheck .hc_types.viewtype .editCheck").attr("disabled", "disabled");
        $(".viewStatus 	.progressStatusMessage").hide();
        $(".viewStatus 	.errorSupport").show();
        $(".viewStatus 	.errorSupport .errorMessage").html("Health check not supported on this operating system. Use windows machine to run VMware View health check.");
    }
    
    $( "#foundation_server_ip" ).keyup(function( event ) {
        var ipRegex=/^(?!0)(?!.*\.$)((1?\d?\d|25[0-5]|2[0-4]\d)(\.|$)){4}$/;
        var inputVal = $(this).val();
        if((inputVal).match(ipRegex))
        {
            var post_data = {};
            post_data["foundationVM"] = inputVal;
            $('#phonix_iso').find('option:gt(0)').remove();
            $('#hypervisor_iso').find('option:gt(0)').remove();
            $.ajax({
                url: '/isoImages/',
                type: "POST",
                dataType: "json",
                data: JSON.stringify(post_data),
                success: function(data) {
                    for(var i=0;i<data.images.nos.length;i++){
                        $('#phonix_iso').append($('<option>', { 
                            value: data.images.nos[i],
                            text : data.images.nos[i]
                        }));
                    }
                    for(var j=0;j<data.images.hypervisor.length;j++){
                        $('#hypervisor_iso').append($('<option>', { 
                            value: data.images.hypervisor[j],
                            text : data.images.hypervisor[j]
                        }));
                    }
                },
            });
        }
    });
});