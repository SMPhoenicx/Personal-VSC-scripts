package Java;

public class DLink<D> {
    public D value; //holds value
    public DLink<D> next; //holds next link
    public DLink<D> prev; //holds previous link

    public DLink(D val) //constructor
    {
        value = val;
        next = null;
        prev = null;
    }

    public void addNext(DLink<D> next) //change next value
    {
        this.next = next;
    }

    public void addPrev(DLink<D> prev) //change prev value
    {
        this.prev = prev;
    }
}