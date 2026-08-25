/* LOGEO - route rendering patch */
(function(){
const oldFetch=window.fetch;
if(!oldFetch)return;
function decodeShape(s){if(!s)return null;if(typeof s==='object')return s;try{return JSON.parse(s)}catch(e){return null}}
window.logeoDecodeRouteShape=decodeShape;
const style=document.createElement('style');style.textContent='.logeo-route-map{height:300px!important;min-height:250px;background:#e9eef2;border-radius:12px;overflow:hidden;border:1px solid #d6dbe5;margin-top:12px}@media(max-width:650px){.logeo-route-map{height:250px!important}}';document.head.appendChild(style);
const previousOpen=window.openListingDetail;
window.openListingDetail=function(id){
 if(typeof previousOpen==='function')previousOpen(id);
 setTimeout(()=>{const map=document.getElementById('routeMap');if(!map||typeof L==='undefined')return;map.dataset.routeFix='1';},700);
};
})();