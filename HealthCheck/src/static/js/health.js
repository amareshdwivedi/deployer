<script type="text/javascript" >
jQuery(document).ready(function(){
    jQuery("#runnhecks").click(function() {
        var looping = true
        var inputElements = document.getElementsByClassName('run');
        checks = [];
        for(var i=0; inputElements[i]; ++i)
        {
            checks.push({name: inputElements[i].name, value: inputElements[i].checked});
        }
        checks.push({name: 'operation', value: 'exec_checks'}); 
        console.log(checks)
        jQuery.ajax({
            url: '/',
            type: "POST",
            data: checks,
            success: function(data) {
                looping = false
                alert(data)
            },
        });
        //Get call with refresh timer.
        cont_run = [];
        cont_run.push({name: 'operation', value: 'refresh_logs'});
        setInterval( function(){
                        if(looping = true){
                            jQuery.ajax({
                                url: '/',
                                type: "POST",
                                data: cont_run,
                                success: function(data) {
                                    console.log(looping)
                                    document.getElementById('logs').value = data;
                                 },
                             });
                      }},10000)


        //polling().done(function(){setTimeout(polling, 20000);});       
    return false;
    });

    jQuery(".conf").click(function() {
        if ($$(this).attr('id')=="config_vc") {
            var form_data = $$("#vc").serializeArray();
            form_data.push({name: 'operation', value: 'config_vc'});
            console.log(form_data)
                jQuery.ajax({
                //url: '/',
                type: "POST",
                dataType: "json",
                data: form_data,
                success: function(value) {
                    console.log(value)
                    alert("Successfully Updated")
                },
            });
        }
        if ($$(this).attr('id')=="config_ncc") {
            
            var form_data = $$("#ncc").serializeArray();
            form_data.push({name: 'operation', value: 'config_ncc'});
            jQuery.ajax({
                //url: '/',
                type: "POST",
                //contentType: 'application/x-www-form-urlencoded',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    alert("Successfully Updated")
                    console.log(data)
                },
            });
        }
    return false;
    });

    jQuery(".conn").click(function() {
        if ($$(this).attr('id')=="connect_vc") {
            var form_data = $$("#vc").serializeArray();
            form_data.push({name: 'operation', value: 'connect_vc'});

                jQuery.ajax({
                //url: '/',
                type: "POST",
                //contentType: 'application/x-www-form-urlencoded',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    console.log(data)
                    var status=data["Connection"];
                    console.log(status)
                    alert("Connection "+status)
                },
            });
        }
        if ($$(this).attr('id')=="connect_ncc") {
            var form_data = $$("#ncc").serializeArray();
            form_data.push({name: 'operation', value: 'connect_ncc'});

            jQuery.ajax({
                //url: '/',
                type: "POST",
                //contentType: 'application/x-www-form-urlencoded',
                dataType: "json",
                data: form_data,
                success: function(data) {
                    console.log(data)
                    var status=data["Connection"];
                    console.log(status)
                    alert("Connection "+status)
                },
            });
        }
    return false;
    });
});
</script>
