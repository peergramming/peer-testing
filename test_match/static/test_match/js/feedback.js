/*
Manage tab selection in feedback view
 */

document.addEventListener('DOMContentLoaded', function() {
$(".file_tab").on("click", function(){
        var dataid = this.attributes['data-id'].value;
        var active = $(".active");
        active.removeClass("active");
        active.addClass("inactive");
        var selector = ".inactive[data-id='" + dataid +"']";
        var selected = $(selector)
        selected.removeClass("inactive")
        selected.addClass("active")
        if(dataid===""){
                $("#file_view p").removeClass("inactive");
                $("#file_view p").addClass("active");
        }
})
});