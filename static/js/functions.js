function post(){
var number = $("#number").val()
$.post('/login',{number:number},
function(data){
$('.main-left').html(data);
$("#number").val('');
});
}

$('form').submit(function(e) {
    e.preventDefault();
});

function startTime()
{
var today=new Date();
var h=today.getHours();
var m=today.getMinutes();
var s=today.getSeconds();

if (h >= 12){
	ap = "PM"
}else{
	ap = "AM"
}

if (h > 12) {
        h -= 12;
    } else if (h === 0) {
        h = 12;
    }


// add a zero in front of numbers<10
m=checkTime(m);
s=checkTime(s);
document.getElementById('time').innerHTML=h+":"+m+" "+ap;
t=setTimeout('startTime()',500);
}
function checkTime(i)
{
if (i<10)
{
i="0" + i;
}
return i;
}